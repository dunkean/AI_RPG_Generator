"""Browser generation validates inputs, isolates archives and reports job failures."""

import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from src.genealogy.config import Scenario
from src.genealogy.engine import generate
from src.genealogy.server import make_handler
from src.genealogy.store import Archive
from src.genealogy.studio import BusyError, Studio


@pytest.fixture
def studio(tmp_path):
    path = tmp_path / "initial.sqlite"
    generate(Scenario(initial_population=40, years=3), path)
    return Studio(Archive(path), tmp_path / "runs")


def test_job_generation_determinism_archive_selection_and_restart(studio):
    original = studio.current().path
    source = Scenario(seed=9876, initial_population=100, years=12).model_dump(mode="json")
    outputs = []
    for _ in range(2):
        job = studio.start({"scenario": source})
        studio.worker.join(timeout=10)
        assert not studio.worker.is_alive()
        status = studio.status()
        assert status["state"] == "complete" and status["progress"] == 1
        assert studio.current().path == original  # completion cannot disrupt ongoing exploration
        assert status["archive"] == f"world_{job['id']}"
        outputs.append(studio.archives[status["archive"]].overview())
    assert outputs[0]["history"] == outputs[1]["history"]
    assert outputs[0]["summary"]["people_ever"] == outputs[1]["summary"]["people_ever"]
    studio.select(status["archive"])
    assert studio.config()["seed"] == 9876
    assert len(studio.catalogue()["archives"]) == 3
    restored = Studio(Archive(original), studio.output_dir)
    assert len(restored.catalogue()["archives"]) == 3
    assert status["archive"] in restored.archives
    with pytest.raises(KeyError):
        restored.select("../../arbitrary.sqlite")


def test_job_busy_failure_and_retry(studio, monkeypatch):
    entered, release = threading.Event(), threading.Event()

    def fail(*args, **kwargs):
        entered.set()
        assert release.wait(timeout=5)
        args[1].parent.mkdir(parents=True, exist_ok=True)
        args[1].with_suffix(".sqlite.partial").write_text("interrupted")
        raise RuntimeError("Simulation failure")

    monkeypatch.setattr("src.genealogy.studio.generate", fail)
    payload = {"scenario": {"initial_population": 30, "years": 2}}
    studio.start(payload)
    assert entered.wait(timeout=5)
    try:
        with pytest.raises(BusyError):
            studio.start(payload)
    finally:
        release.set()
        studio.worker.join(timeout=5)
    assert studio.status()["state"] == "failed"
    assert studio.status()["error"] == "Simulation failure"
    assert not list(studio.output_dir.glob("*.partial"))
    studio.start(payload)
    studio.worker.join(timeout=5)
    assert studio.status()["state"] == "failed"


def test_catalogue_survives_missing_and_corrupt_archives(studio):
    studio.start({"scenario": {"initial_population": 30, "years": 2}})
    studio.worker.join(timeout=10)
    key = studio.status()["archive"]
    studio.archives[key].path.unlink()
    assert [a["id"] for a in studio.catalogue()["archives"]] == ["initial"]
    (studio.output_dir / "world_bad.sqlite").write_bytes(b"not a database")
    restored = Studio(studio.current(), studio.output_dir)
    assert len(restored.catalogue()["archives"]) == 1


def test_target_regulation_uses_one_run(studio):
    studio.start(
        {
            "scenario": {
                "target_population": 100,
                "calibration_population": 100,
                "initial_population": 30,
                "years": 2,
            }
        }
    )
    studio.worker.join(timeout=10)
    assert studio.status()["state"] == "complete"
    assert studio.status()["summary"]["calibration"] is None
    assert studio.status()["summary"]["simulation_runs"] == 1
    assert studio.status()["summary"]["initial_population"] == 30


def test_single_run_progress_never_restarts(studio, monkeypatch):
    from src.genealogy.engine import generate as real_generate

    observations, calls = [], []

    def controlled(config, path, progress):
        calls.append((config.initial_population, config.seed))

        def observed(year, count):
            progress(year, count)
            observations.append(studio.status())

        return real_generate(config, path, observed)

    monkeypatch.setattr("src.genealogy.studio.generate", controlled)
    studio.start(
        {
            "scenario": {
                "initial_population": 30,
                "target_population": 100,
                "years": 4,
                "target_mode": "calibrate_founders",
            }
        }
    )
    studio.worker.join(timeout=10)
    assert studio.status()["state"] == "complete"
    assert len(calls) == 1
    assert calls[0][0] == 30
    assert [row["year"] for row in observations] == [1001, 1002, 1003, 1004]
    assert [row["progress"] for row in observations] == [0.25, 0.5, 0.75, 1]
    assert all("calibration_pass" not in row for row in observations)


def test_studio_http_validation_generation_assets_and_origin(studio):
    with ThreadingHTTPServer(("127.0.0.1", 0), make_handler(studio.current(), studio)) as server:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        root = f"http://127.0.0.1:{server.server_port}"

        def post(route, payload, origin=root):
            request = Request(
                root + route,
                json.dumps(payload).encode(),
                {"Content-Type": "application/json", "Origin": origin},
            )
            with urlopen(request, timeout=5) as response:
                return response.status, json.load(response)

        try:
            for asset, mime in [
                ("/studio.css", "text/css"),
                ("/studio.js", "application/javascript"),
            ]:
                with urlopen(root + asset, timeout=5) as response:
                    assert response.headers["Content-Type"].startswith(mime)
                    assert len(response.read()) > 100
            code, value = post("/api/validate", {"yaml": "seed: 812\nyears: 3"})
            assert code == 200 and value["scenario"]["seed"] == 812
            for payload in [{"scenario": {"seed": -1}}, {"yaml": "races: ["}]:
                with pytest.raises(HTTPError) as error:
                    post("/api/generate", payload)
                assert error.value.code == 400
            assert studio.status()["state"] == "idle"
            with pytest.raises(HTTPError) as error:
                post("/api/generate", {"scenario": {}}, "https://example.invalid")
            assert error.value.code == 403
            code, value = post(
                "/api/generate", {"scenario": {"seed": 812, "initial_population": 50, "years": 5}}
            )
            assert code == 202
            studio.worker.join(timeout=10)
            with urlopen(root + "/api/job", timeout=5) as response:
                status = json.load(response)
            assert status["state"] == "complete"
            post("/api/select", {"id": status["archive"]})
            with urlopen(root + "/api/config", timeout=5) as response:
                assert json.load(response)["seed"] == 812
            with urlopen(root + "/api/world?archive=initial", timeout=5) as response:
                bundle = json.load(response)
            assert bundle["archive"] == "initial"
            assert bundle["config"]["seed"] == 42
        finally:
            server.shutdown()
            worker.join(timeout=5)


def test_cancelled_job_does_not_publish_archive_and_can_retry(studio, monkeypatch):
    from src.genealogy.engine import generate as real_generate

    entered, release = threading.Event(), threading.Event()

    def paused(config, path, progress, **kwargs):
        entered.set()
        assert release.wait(timeout=5)
        progress(config.start_year + 1, config.initial_population)

    monkeypatch.setattr("src.genealogy.studio.generate", paused)
    studio.start({"scenario": {"initial_population": 30, "years": 2}})
    assert entered.wait(timeout=5)
    studio.cancel()
    release.set()
    studio.worker.join(timeout=5)
    assert studio.status()["state"] == "cancelled"
    assert len(studio.catalogue()["archives"]) == 1
    assert not list(studio.output_dir.glob("*.partial"))
    monkeypatch.setattr("src.genealogy.studio.generate", real_generate)
    studio.start({"scenario": {"initial_population": 30, "years": 2}})
    studio.worker.join(timeout=10)
    assert studio.status()["state"] == "complete"
