"""Pipeline runs in background threads, with a log and a progress report the browser polls.

Each book has its own queue. Nothing asked for is refused because something else is running: it waits its turn.
Work runs on two lanes at once:
  - "main": drawing (all art, a pilot, redraws) and building;
  - "text": Claude rewriting book.yaml for word and layout fixes.
So a picture redraw and a word fix go ahead side by side. A build reads the whole book, so it waits until
nothing else is running or waiting before it, and is kept at the end of the queue: one rebuild after the fixes.

Redraws waiting in the queue are merged into one job, whose pictures are then drawn at the same time
(generate.run draws a group in parallel). Word fixes waiting are merged into one job too, and made one after
another (each one rewrites the same book.yaml)."""
from __future__ import annotations

import asyncio
import contextvars
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field

from rich.text import Text

from .. import author, control, settings
from ..art import generate
from ..art.lint import lint
from ..imaging import margins
from ..layout.cover import build_cover
from ..layout.render import build_interior
from ..preflight import check, proofs
from ..project import Project
from . import state

KINDS = ("mock", "pilot", "art", "regen", "build", "margins", "text", "check")
BUILDS = ("mock", "build", "check")     # read the whole built book: run after every edit before them
REDRAWS = ("regen", "margins")
ACTIVE = ("queued", "running")
KEEP_DONE = 30 * 60                     # finished jobs stay listed for the book this long (seconds)

# the steps of a build, with their rough share of its time (laying out the pages is the slow part)
BUILD_STAGES = [("layout", "Laying out the pages", 50), ("cover", "Making the cover", 10),
                ("preflight", "Checking against KDP's rules", 15), ("proofs", "Making the page previews", 25)]


@dataclass
class Job:
    id: str
    slug: str
    kind: str
    status: str = "queued"    # queued | running | done | failed | cancelled
    lines: list[str] = field(default_factory=list)
    result: dict = field(default_factory=dict)
    created: float = field(default_factory=time.time)
    started: float = 0.0
    ended: float = 0.0
    user: str | None = None   # the account that started it (None: single-user studio)
    ctx: contextvars.Context | None = field(default=None, repr=False)
    # what it works on
    redraw: dict[str, str | None] = field(default_factory=dict)   # slot -> the note to redraw it with
    fit: list[str] = field(default_factory=list)                   # slots to redraw inside the margin
    texts: list[dict] = field(default_factory=list)                # word fixes: {issue, prompt}
    issues: dict[str, str] = field(default_factory=dict)           # control issue -> slot it redraws
    pilot_pages: int = 3
    force: bool = False
    # live progress
    stages: list[tuple[str, str, int]] = field(default_factory=list)
    stage: str = ""
    stage_done: dict[str, float] = field(default_factory=dict)
    total: int = 0
    phase: str = ""
    active: list[str] = field(default_factory=list)
    images: list[dict] = field(default_factory=list)   # finished images, in the order they landed
    note: str = ""            # what it is doing right now, in words (a word fix, a page being read)

    @property
    def lane(self) -> str:
        return "text" if self.kind == "text" else "main"

    @property
    def slots(self) -> list[str]:
        return list(dict.fromkeys([*self.redraw, *self.fit]))

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
        if self.total:
            self.stage_done["draw"] = len(self.images) / self.total

    def enter(self, stage: str) -> None:
        """Mark the stages before `stage` finished and `stage` the current one."""
        for k, _, _ in self.stages:
            if k == stage:
                break
            self.stage_done[k] = 1.0
        self.stage = stage
        self.stage_done.setdefault(stage, 0.0)

    def log(self, msg: str) -> None:
        self.lines.append(Text.from_markup(str(msg)).plain)

    def percent(self) -> int:
        if self.status == "done":
            return 100
        weight = sum(w for _, _, w in self.stages)
        if not weight:
            return 0
        return min(99, round(100 * sum(w * self.stage_done.get(k, 0.0) for k, _, w in self.stages) / weight))

    def summary(self) -> dict:
        """Everything the activity panel shows, without the log."""
        q = QUEUE.get((self.user, self.slug), [])
        ahead = [j for j in q[:q.index(self)]] if self in q else []
        return {"id": self.id, "slug": self.slug, "kind": self.kind, "status": self.status,
                "created": self.created, "started": self.started, "ended": self.ended, "now": time.time(),
                "redraw": list(self.redraw), "fit": list(self.fit),
                "texts": [{"issue": t["issue"], "page": t.get("page")} for t in self.texts],
                "issues": dict(self.issues), "pilot_pages": self.pilot_pages,
                "waits_for": [j.id for j in ahead if self.status == "queued"],
                "error": self.result.get("error"), "failures": self.result.get("failures") or {},
                "log_n": len(self.lines),
                "progress": {"pct": self.percent(), "stage": self.stage, "note": self.note,
                             "stages": [{"key": k, "label": l, "done": self.stage_done.get(k, 0.0) >= 1 or self.status == "done"}
                                        for k, l, _ in self.stages],
                             "total": self.total, "done": len(self.images), "phase": self.phase,
                             "active": list(self.active), "images": list(self.images)}}

    def view(self, since: int = 0) -> dict:
        return {**self.summary(), "lines": self.lines[since:], "next": len(self.lines), "result": self.result}


JOBS: dict[str, Job] = {}
QUEUE: dict[tuple, list[Job]] = {}     # (user, slug) -> its queued and running jobs, in order
_lock = threading.RLock()


def _key(slug: str) -> tuple:
    return settings.current_user.get(), slug


def running(slug: str) -> Job | None:
    """The first job running or waiting for this book."""
    return next(iter(QUEUE.get(_key(slug), [])), None)


def busy() -> bool:
    return any(j.status in ACTIVE for j in JOBS.values())


def get(job_id: str) -> Job | None:
    """A job, only for the account that started it."""
    j = JOBS.get(job_id)
    return j if j and j.user == settings.current_user.get() else None


def book_jobs(slug: str) -> list[dict]:
    """The book's jobs running and waiting, in order, then the ones that finished lately (newest first)."""
    key = _key(slug)
    now = time.time()
    with _lock:
        active = list(QUEUE.get(key, []))
        ended = sorted((j for j in JOBS.values() if (j.user, j.slug) == key and j.status not in ACTIVE
                        and j.status != "cancelled" and now - j.ended < KEEP_DONE), key=lambda j: -j.ended)
        return [j.summary() for j in active + ended[:8]]


def issue_jobs(slug: str) -> dict[str, dict]:
    """For every control issue waiting or being fixed: the job doing it."""
    out = {}
    with _lock:
        for j in QUEUE.get(_key(slug), []):
            for iid in [*j.issues, *(t["issue"] for t in j.texts)]:
                out[iid] = {"id": j.id, "status": j.status, "kind": j.kind}
    return out


def _join(a: str | None, b: str | None) -> str | None:
    if a and b and b not in a:
        return f"{a} Also: {b}"
    return a or b


def start(slug: str, kind: str, slots: list[str] | None = None, note: str | None = None,
          pilot_pages: int = 3, force: bool = False, notes: dict[str, str | None] | None = None,
          issues: dict[str, str] | None = None, texts: list[dict] | None = None,
          then_build: bool = False) -> Job:
    """Queue some work for the book and return the job that will do it. A redraw or word fix joins one of
    the same sort still waiting; `then_build` makes sure the book is built again once it is done."""
    if kind not in KINDS:
        raise ValueError(f"unknown job {kind!r}")
    key = _key(slug)
    with _lock:
        q = QUEUE.setdefault(key, [])
        waiting = [j for j in q if j.status == "queued"]
        if kind in ("art", "pilot") and any(j.kind in ("art", "pilot") for j in q):
            raise RuntimeError("the pictures are already being drawn - see the progress at the top")
        if kind in REDRAWS:
            job = next((j for j in waiting if j.kind in REDRAWS), None)
        elif kind == "text":
            job = next((j for j in waiting if j.kind == "text"), None)
        elif kind in BUILDS:
            job = next((j for j in waiting if j.kind == kind), None)
        else:
            job = None
        if job is None:
            job = Job(uuid.uuid4().hex[:12], slug, kind, user=key[0], ctx=contextvars.copy_context(),
                      pilot_pages=pilot_pages, force=force)
            JOBS[job.id] = job
            # a build waits at the end, so it shows everything queued before it
            at = next((i for i, j in enumerate(q) if j.status == "queued" and j.kind in BUILDS), len(q)) \
                if kind not in BUILDS else len(q)
            q.insert(at, job)
        if kind == "regen":
            for s in slots or []:
                job.redraw[s] = _join(job.redraw.get(s), (notes or {}).get(s, note))
            if job.kind == "margins":
                job.kind = "regen"      # a mix: some redrawn with a note, some inside the margin
        elif kind == "margins":
            job.fit += [s for s in slots or [] if s not in job.fit]
        job.issues.update(issues or {})
        job.texts += [t for t in texts or [] if all(t["issue"] != x["issue"] for x in job.texts)]
        if then_build:
            ensure_build(slug)
        _pump(key)
        return job


def ensure_build(slug: str) -> None:
    """Make sure the book is built again after everything queued: one build waiting at the end."""
    key = _key(slug)
    with _lock:
        q = QUEUE.setdefault(key, [])
        if not any(j.status == "queued" and j.kind in BUILDS for j in q):
            b = Job(uuid.uuid4().hex[:12], slug, "build", user=key[0], ctx=contextvars.copy_context())
            JOBS[b.id] = b
            q.append(b)
        _pump(key)


def cancel(job_id: str) -> bool:
    """Take a job that has not started out of the queue."""
    with _lock:
        j = get(job_id)
        if not j or j.status != "queued":
            return False
        _drop(j)
        return True


def drop_issue(slug: str, issue_id: str) -> bool:
    """Take one control fix out of the job still waiting to do it (the job goes when it has nothing left)."""
    with _lock:
        for j in QUEUE.get(_key(slug), []):
            if j.status != "queued":
                continue
            if issue_id in j.issues:
                slot = j.issues.pop(issue_id)
                if slot not in j.issues.values():
                    j.redraw.pop(slot, None)
                    if slot in j.fit:
                        j.fit.remove(slot)
            elif any(t["issue"] == issue_id for t in j.texts):
                j.texts = [t for t in j.texts if t["issue"] != issue_id]
            else:
                continue
            if not j.slots and not j.texts:
                _drop(j)
            return True
    return False


def _drop(j: Job) -> None:
    j.status, j.ended = "cancelled", time.time()
    q = QUEUE.get((j.user, j.slug), [])
    if j in q:
        q.remove(j)
    # a rebuild left with nothing before it that changes the book is still worth doing: it stays
    _pump((j.user, j.slug))


def _pump(key: tuple) -> None:
    """Start every waiting job of the book that may run now. Each lane runs one job at a time, in order;
    a build only starts when nothing runs and nothing waits before it."""
    with _lock:
        q = QUEUE.get(key, [])
        blocked: set[str] = set()
        for i, j in enumerate(q):
            if j.status == "running":
                blocked.add(j.lane)
                continue
            if j.lane in blocked:
                continue
            busy_now = [x for x in q if x.status == "running"]
            if j.kind in BUILDS:
                ok = not busy_now and not any(x.status == "queued" for x in q[:i])
            else:
                ok = not any(x.kind in BUILDS for x in busy_now)
            if not ok:
                blocked.add(j.lane)
                continue
            j.status, j.started = "running", time.time()
            blocked.add(j.lane)
            threading.Thread(target=j.ctx.copy().run, args=(_run, j), daemon=True).start()


def _redraw(job: Job, p: Project) -> None:
    """Redraw pictures: each with its note, or again inside the margin from a layout draft of its current
    picture (imaging.margins). All of them are drawn at the same time. The book is laid out first when the last
    build does not say where a picture to fit sits."""
    measure = bool(job.fit) and any(margins.placement(p, s) is None for s in job.fit)
    job.stages = ([("measure", "Measuring where each picture sits", 25)] if measure else []) + \
        [("draw", f"Drawing {len(job.slots)} picture{'s' if len(job.slots) > 1 else ''} at the same time"
          if len(job.slots) > 1 else "Drawing the picture", 75)]
    if measure:
        job.enter("measure")
        job.log("laying out the book to measure where each picture sits…")
        build_interior(p)
    drafts, skipped = {}, {}
    for sid in job.fit:
        if d := margins.draft(p, sid):
            drafts[sid] = d
        else:
            skipped[sid] = "nothing to redraw: no picture, a two-page spread, or already inside the margin"
            job.log(f"  {sid}: skipped ({skipped[sid]})")
    todo = set(job.redraw) | set(drafts)
    job.enter("draw")
    failures = {}
    if todo:
        notes = {s: n for s, n in job.redraw.items() if n}
        failures = generate.run(p, only=todo, bump=todo, notes=notes or None, drafts=drafts or None,
                                log=job.log, progress=job.on_progress) or {}
    for sid, why in failures.items():
        job.log(f"NEEDS ATTENTION {sid}: {why}")
    job.result["failures"] = failures
    # the control issues behind it: fixed when their picture was drawn again, or why not
    failed = {x["id"]: x["result"] for x in job.images if x["failed"]}
    for iid, sid in job.issues.items():
        why = skipped.get(sid) or failed.get(sid) or (None if sid in todo else "the picture was not drawn")
        _mark(p, iid, why)


def _mark(p: Project, issue_id: str, error: str | None) -> None:
    try:
        control.set_status(p, issue_id, "open" if error else "applied", error=error or "")
    except KeyError:
        pass   # the book was checked again meanwhile: that issue is gone


def _texts(job: Job, p: Project) -> None:
    """Make the word and layout fixes one after another: each one rewrites book.yaml. A fix whose words are
    lettered into a picture (t["redraw"] = its slot) then queues that picture to be drawn from the new words:
    the issue is fixed when the redraw is."""
    job.stages = [("write", f"Fixing the words ({len(job.texts)})" if len(job.texts) > 1 else "Fixing the words", 100)]
    job.enter("write")
    done = 0
    for k, t in enumerate(list(job.texts)):
        report = control.load(p) or {"issues": []}
        issue = next((i for i in report["issues"] if i["id"] == t["issue"]), None)
        job.note = f"page {issue['page']}: {issue['problem']}" if issue else ""
        job.log(f"fix {k + 1} of {len(job.texts)}: {job.note}")
        try:
            if not issue:
                raise KeyError("the book was checked again meanwhile: this problem is gone")
            brief = state.load_state(job.slug).get("brief")
            if slot := t.get("redraw"):
                now = control.lettering_of(Project(p.book_path), slot)
                if issue.get("current") and issue.get("replace_with") and not control.wrong_in_manuscript(issue, now):
                    job.log("  book.yaml already has the right words")   # fixed meanwhile by another fix
                else:
                    state.write_yaml(job.slug, asyncio.run(control.apply_manuscript(
                        state.read_yaml(job.slug), issue, t["prompt"], brief)))
                    job.log("  words fixed in book.yaml")
                start(job.slug, "regen", slots=[slot], notes={slot: t["prompt"]}, issues={t["issue"]: slot})
                job.log(f"  {slot}: queued to be drawn again with the new words")
            else:
                text = asyncio.run(control.apply_text(state.read_yaml(job.slug), issue, t["prompt"], brief))
                state.write_yaml(job.slug, text)
                control.set_status(p, t["issue"], "applied", t["prompt"], error="")
                job.log("  done")
            done += 1
        except Exception as e:   # one fix that fails does not stop the others
            msg = str(e.args[0]) if isinstance(e, KeyError) and e.args else str(e)
            job.log(f"FAILED: {msg}")
            if issue:
                _mark(p, t["issue"], msg)
        job.stage_done["write"] = (k + 1) / len(job.texts)
    job.note = ""
    if not done:
        raise RuntimeError("no fix could be made - see each problem below")
    if done < len(job.texts):
        job.result["error"] = f"{len(job.texts) - done} of {len(job.texts)} fixes could not be made"


def _build(job: Job, p: Project, mock: bool) -> None:
    job.enter("layout")
    m = build_interior(p)
    job.log(f"interior: {m['pages']} pages")
    job.enter("cover")
    c = build_cover(p)
    job.log(f"cover: {c['size_in'][0]:.3f} x {c['size_in'][1]:.3f} in, spine {c['spine_in']:.3f} in")
    job.enter("preflight")
    report = check(p)
    job.enter("proofs")
    proofs(p)
    job.stage_done["proofs"] = 1.0
    for e in report["errors"]:
        job.log(f"ERROR {e}")
    for w in report["warnings"]:
        job.log(f"WARN  {w}")
    job.log(f"preflight {'PASS' if report['ok'] else 'FAIL'}")
    job.result["preflight"] = report
    state.save_state(job.slug, last_build="mock" if mock else "real")


def _read(job: Job, p: Project) -> None:
    """Claude reads every built page (control & correction)."""
    job.enter("read")

    def tick(done: int, total: int) -> None:
        job.stage_done["read"] = done / total if total else 1.0
        job.note = f"{done} of {total} groups of pages read"

    report = asyncio.run(control.inspect(p, progress=tick))
    n = sum(1 for i in report["issues"] if i["status"] == "open")
    job.log(f"{n} problem{'s' if n != 1 else ''} found on {report['pages']} pages")
    job.result["found"] = n
    job.note = ""


def _run(job: Job) -> None:
    p = None
    try:
        if job.user is None:
            settings.load().apply_env()
        mock = job.kind == "mock"
        p = Project(state.book_dir(job.slug) / "book.yaml", mock)
        drawing = job.kind in ("mock", "pilot", "art")
        build_w = 30 if job.kind == "mock" else 40 if job.kind == "check" else 100
        job.stages = ([("draw", "Drawing the pictures" if job.kind != "mock" else "Placing placeholder pictures",
                        70 if job.kind == "mock" else 100)] if drawing else []) + \
            ([(k, l, w * build_w // 100) for k, l, w in BUILD_STAGES] if job.kind in BUILDS else []) + \
            ([("read", "Claude reads every page", 60)] if job.kind == "check" else [])
        if job.kind in ("pilot", "art"):
            issues = lint(p.book)
            for i in issues:
                job.log(f"{i.level.upper():5} {i.where}: {i.message}")
            if any(i.level == "error" for i in issues) and not job.force:
                raise RuntimeError("prompt check found errors - fix them or run again with 'ignore prompt errors'")
        if drawing:
            job.enter("draw")
            failures = generate.run(p, pilot=job.pilot_pages if job.kind == "pilot" else 0,
                                    log=job.log, progress=job.on_progress)
            for sid, why in (failures or {}).items():
                job.log(f"NEEDS ATTENTION {sid}: {why}")
            job.result["failures"] = failures or {}
        if job.kind in REDRAWS:
            _redraw(job, p)
        if job.kind == "text":
            _texts(job, p)
        if job.kind in BUILDS:
            _build(job, p, mock)
        if job.kind == "check":
            _read(job, p)
        job.status = "done"
    except Exception as e:
        msg = str(e.args[0]) if isinstance(e, KeyError) and e.args else str(e)
        if isinstance(e, author.AuthorError) or not job.result.get("error"):
            job.result["error"] = msg
        job.log(f"FAILED: {msg}")
        job.result["traceback"] = traceback.format_exc()
        job.status = "failed"
        if p is not None and job.kind in REDRAWS:   # the fixes it carried were not made
            for iid in job.issues:
                _mark(p, iid, msg)
    finally:
        job.ended = time.time()
        with _lock:
            q = QUEUE.get((job.user, job.slug), [])
            if job in q:
                q.remove(job)
            _pump((job.user, job.slug))
