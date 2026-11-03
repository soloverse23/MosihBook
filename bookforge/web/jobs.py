"""Pipeline runs in background threads, with a log the browser polls."""
from __future__ import annotations

import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field

from rich.text import Text

from .. import settings
from ..art import generate
from ..art.lint import lint
from ..layout.cover import build_cover
from ..layout.render import build_interior
from ..preflight import check, proofs
from ..project import Project
from . import state

KINDS = ("mock", "pilot", "art", "regen", "build")


@dataclass
class Job:
    id: str
    slug: str
    kind: str
    status: str = "running"   # running | done | failed
    lines: list[str] = field(default_factory=list)
    result: dict = field(default_factory=dict)
    started: float = field(default_factory=time.time)
    ended: float = 0.0
    # live image progress: filled by generate.run's progress callback
    total: int = 0
    phase: str = ""
    active: list[str] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)   # finished images, in the order they landed

    def on_progress(self, event: str, slot_id: str, info) -> None:
        if event == "total":
            self.total = int(info)
        elif event == "phase":
            self.phase = slot_id
        elif event == "start":
            self.active.append(slot_id)
        elif event == "done":
            if slot_id in self.active:
                self.active.remove(slot_id)
            text = str(info)
            self.images.append({"id": slot_id, "result": text, "t": time.time(),
                                "failed": text.startswith("FAILED")})

    def log(self, msg: str) -> None:
        self.lines.append(Text.from_markup(str(msg)).plain)

    def view(self, since: int = 0) -> dict:
        return {"id": self.id, "slug": self.slug, "kind": self.kind, "status": self.status,
                "lines": self.lines[since:], "next": len(self.lines), "result": self.result,
                "started": self.started, "ended": self.ended, "now": time.time(),
                "progress": {"total": self.total, "done": len(self.images), "phase": self.phase,
                             "active": list(self.active), "images": list(self.images)}}


JOBS: dict[str, Job] = {}
_lock = threading.Lock()


def running(slug: str) -> Job | None:
    return next((j for j in JOBS.values() if j.slug == slug and j.status == "running"), None)


def start(slug: str, kind: str, slots: list[str] | None = None, note: str | None = None,
          pilot_pages: int = 3, force: bool = False) -> Job:
    if kind not in KINDS:
        raise ValueError(f"unknown job {kind!r}")
    with _lock:
        if running(slug):
            raise RuntimeError("a job is already running for this book")
        job = Job(uuid.uuid4().hex[:12], slug, kind)
        JOBS[job.id] = job
    threading.Thread(target=_run, args=(job, slots, note, pilot_pages, force), daemon=True).start()
    return job


def _run(job: Job, slots, note, pilot_pages, force) -> None:
    try:
        settings.load().apply_env()
        mock = job.kind == "mock"
        p = Project(state.book_dir(job.slug) / "book.yaml", mock)
        if job.kind in ("pilot", "art"):
            issues = lint(p.book)
            for i in issues:
                job.log(f"{i.level.upper():5} {i.where}: {i.message}")
            if any(i.level == "error" for i in issues) and not force:
                raise RuntimeError("prompt check found errors - fix them or run again with 'ignore prompt errors'")
        if job.kind in ("mock", "pilot", "art", "regen"):
            failures = generate.run(
                p, only=set(slots) if job.kind == "regen" else None,
                bump=set(slots) if job.kind == "regen" else frozenset(),
                notes={s: note for s in slots} if job.kind == "regen" and note else None,
                pilot=pilot_pages if job.kind == "pilot" else 0, log=job.log, progress=job.on_progress)
            for sid, why in (failures or {}).items():
                job.log(f"NEEDS ATTENTION {sid}: {why}")
            job.result["failures"] = failures or {}
        if job.kind in ("mock", "build"):
            m = build_interior(p)
            job.log(f"interior: {m['pages']} pages")
            c = build_cover(p)
            job.log(f"cover: {c['size_in'][0]:.3f} x {c['size_in'][1]:.3f} in, spine {c['spine_in']:.3f} in")
            report = check(p)
            proofs(p)
            for e in report["errors"]:
                job.log(f"ERROR {e}")
            for w in report["warnings"]:
                job.log(f"WARN  {w}")
            job.log(f"preflight {'PASS' if report['ok'] else 'FAIL'}")
            job.result["preflight"] = report
            state.save_state(job.slug, last_build="mock" if mock else "real")
        job.status = "done"
        job.ended = time.time()
    except Exception as e:
        job.log(f"FAILED: {e}")
        job.result["traceback"] = traceback.format_exc()
        job.status = "failed"
        job.ended = time.time()
