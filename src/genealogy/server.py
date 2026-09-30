"""Loopback studio: asynchronous generation and bounded read-only archive views."""

from __future__ import annotations

import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import yaml

from .store import Archive
from .studio import BusyError, Studio


def make_handler(archive: Archive, studio: Studio | None = None):
    studio = studio or Studio(archive)

    class Handler(BaseHTTPRequestHandler):
        def reply(self, value, status=200):
            body = json.dumps(value, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            # Browser writes must originate on this local server, with JSON content.
            origin = self.headers.get("Origin")
            allowed = {
                f"127.0.0.1:{self.server.server_port}",
                f"localhost:{self.server.server_port}",
            }
            host = self.headers.get("Host")
            if host not in allowed or origin and origin != f"http://{host}":
                self.reply({"error": "Origine refusée"}, 403)
                return
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                self.reply({"error": "Envoyer une configuration JSON"}, 415)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 1_000_000:
                    raise ValueError("Configuration vide ou supérieure à 1 Mo")
                payload = json.loads(self.rfile.read(length))
                route = urlsplit(self.path).path
                if route == "/api/generate":
                    self.reply(studio.start(payload), 202)
                elif route == "/api/validate":
                    self.reply({"scenario": studio.validate(payload).model_dump(mode="json")})
                elif route == "/api/select":
                    self.reply(studio.select(payload["id"]))
                else:
                    self.reply({"error": "Route inconnue"}, 404)
            except BusyError as exc:
                self.reply({"error": str(exc)}, 409)
            except (ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
                self.reply({"error": str(exc)}, 400)

        def do_GET(self):
            path = urlsplit(self.path)
            query = parse_qs(path.query)

            def integer(key, default=0):
                return int(query.get(key, [default])[0])

            try:
                archive_id, archive = studio.snapshot(query.get("archive", [None])[0])
                if path.path in ("/", "/studio.css", "/studio.js"):
                    asset, mime = {
                        "/": ("explorer.html", "text/html; charset=utf-8"),
                        "/studio.css": ("studio.css", "text/css; charset=utf-8"),
                        "/studio.js": ("studio.js", "application/javascript; charset=utf-8"),
                    }[path.path]
                    body = Path(__file__).with_name(asset).read_bytes()
                else:
                    if path.path == "/api/presets":
                        value = studio.presets()
                    elif path.path == "/api/job":
                        value = studio.status()
                    elif path.path == "/api/archives":
                        value = studio.catalogue()
                    elif path.path == "/api/world":
                        value = {
                            "archive": archive_id,
                            "overview": archive.overview(),
                            "config": studio.config(archive),
                        }
                    elif path.path == "/api/config":
                        value = studio.config(archive)
                    elif path.path == "/api/overview":
                        value = archive.overview()
                    elif path.path == "/api/person":
                        value = archive.person(integer("id"))
                    elif path.path == "/api/lineage":
                        value = archive.lineage(
                            integer("id"),
                            integer("depth", 4),
                            query.get("direction", ["ancestors"])[0],
                        )
                    elif path.path == "/api/residents":
                        value = archive.residents(
                            integer("place"), integer("limit", 100), integer("after", -1)
                        )
                    elif path.path == "/api/map":
                        value = archive.map_at(integer("year"))
                    elif path.path == "/api/residence":
                        value = archive.residence(integer("id"), integer("year"))
                    else:
                        self.send_error(404)
                        return
                    body, mime = json.dumps(value, ensure_ascii=False).encode(), "application/json"
                self.send_response(200)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
            except KeyError:
                self.send_error(404, "Unknown individual")
            except (ValueError, OverflowError) as exc:
                self.send_error(400, str(exc))
            except sqlite3.Error:
                self.send_error(500, "Archive query failed")

        def log_message(self, *args):
            pass

    return Handler


def serve(path: Path, port=8765):
    archive = Archive(path)
    with ThreadingHTTPServer(("127.0.0.1", port), make_handler(archive)) as server:
        print(f"Explorer: http://127.0.0.1:{server.server_port} (Ctrl+C to stop)", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
