"""Loopback-only, read-only bounded HTTP views over an archive."""

from __future__ import annotations

import json
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .store import Archive


def make_handler(archive: Archive):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path)
            query = parse_qs(path.query)

            def integer(key, default=0):
                return int(query.get(key, [default])[0])

            try:
                if path.path == "/":
                    body = Path(__file__).with_name("explorer.html").read_bytes()
                    mime = "text/html; charset=utf-8"
                else:
                    if path.path == "/api/overview":
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
