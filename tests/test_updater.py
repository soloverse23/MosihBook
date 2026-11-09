"""Self-update of the Windows install, with GitHub, the installer and the exit stubbed out."""
import hashlib
import io
import zipfile

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from bookforge.web import app as webapp
from bookforge.web import jobs, updater


def test_version_compare():
    assert updater.newer("0.1.1", "0.1.0")
    assert updater.newer("v0.10.0", "0.9.9")
    assert updater.newer("1.0", "0.9.9")
    assert not updater.newer("0.1.0", "0.1.0")
    assert not updater.newer("0.1.0", "0.1.0.0")
    assert not updater.newer("0.0.9", "0.1.0")


def _update_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("MosiBooks/Install-MosiBooks.bat", "@echo off\r\n")
        z.writestr("MosiBooks/payload/uv.exe", b"MZ")
    return buf.getvalue()


@pytest.fixture
def installed(tmp_path, monkeypatch):
    data = _update_zip()
    rel = {"version": "9.9.9", "notes": "Faster pictures", "url": "https://example.test/u.zip",
           "size": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    calls = {"popen": [], "exit": 0}
    monkeypatch.setattr(jobs, "JOBS", {})  # other tests can leave jobs running
    monkeypatch.setattr(updater, "_cache", None)
    monkeypatch.setattr(updater, "_applying", False)
    monkeypatch.setattr(updater, "app_dir", lambda: tmp_path / "app")
    monkeypatch.setattr(updater, "latest_release", lambda: dict(rel))

    class Resp(io.BytesIO):
        def __exit__(self, *a): self.close()
    monkeypatch.setattr(updater, "_get", lambda url, timeout=15: Resp(data))
    monkeypatch.setattr(updater.subprocess, "Popen", lambda cmd, **kw: calls["popen"].append(cmd))

    class Timer:
        def __init__(self, *a): pass
        def start(self): calls["exit"] += 1
    monkeypatch.setattr(updater.threading, "Timer", Timer)
    return tmp_path / "app", rel, calls


def test_off_outside_the_windows_install(monkeypatch):
    monkeypatch.delenv("MOSIBOOKS_APP_DIR", raising=False)
    monkeypatch.setattr(jobs, "JOBS", {})
    c = TestClient(webapp.app)
    assert c.get("/api/update").json()["enabled"] is False
    assert c.post("/api/update/apply").status_code == 400


def test_check_offers_a_newer_release(installed):
    u = TestClient(webapp.app).get("/api/update").json()
    assert u["enabled"] and u["available"] and u["latest"] == "9.9.9" and u["notes"] == "Faster pictures"
    assert "_rel" not in u


def test_apply_unpacks_and_hands_over_to_the_installer(installed):
    app_dir, _, calls = installed
    r = TestClient(webapp.app).post("/api/update/apply")
    assert r.status_code == 200 and r.json()["version"] == "9.9.9"
    installer = app_dir / "update" / "new" / "MosiBooks" / "Install-MosiBooks.bat"
    assert installer.exists()
    assert calls["popen"] and calls["popen"][0][-2:] == [str(installer), "update"]
    assert calls["exit"] == 1


def test_apply_rejects_a_damaged_download(installed, monkeypatch):
    _, rel, calls = installed
    monkeypatch.setattr(updater, "latest_release", lambda: {**rel, "sha256": "0" * 64})
    r = TestClient(webapp.app).post("/api/update/apply")
    assert r.status_code == 400 and "damaged" in r.json()["detail"]
    assert not calls["popen"] and not calls["exit"]


def test_apply_waits_for_running_jobs(installed, monkeypatch):
    monkeypatch.setitem(jobs.JOBS, "j1", jobs.Job(id="j1", slug="b", kind="art"))
    assert TestClient(webapp.app).post("/api/update/apply").status_code == 409


def test_nothing_newer(installed, monkeypatch):
    _, rel, _ = installed
    monkeypatch.setattr(updater, "latest_release", lambda: {**rel, "version": "0.0.1"})
    c = TestClient(webapp.app)
    assert c.get("/api/update").json()["available"] is False
    assert c.post("/api/update/apply").status_code == 400
