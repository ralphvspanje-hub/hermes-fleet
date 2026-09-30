#!/usr/bin/env python3
"""Aristotle teach-MCP: safe, high-level teaching operations for the Aristotle profile.

The chat agent only ever calls these tools; it never gets raw shell/file. Engine
operations (onboard/lesson/feedback) are launched as DETACHED background jobs
(run_teach_async.sh) and return immediately, so the MCP event loop is never
blocked (no keepalive-reconnect kills) and there's no long synchronous spinner.
The detached job records status in <track>/.status.json and pushes the result to
the track's Telegram topic when done. Registry tools manage tracks.json.
"""
import json
import os
import re
import time
import subprocess
import tempfile
import datetime
from pathlib import Path
from html.parser import HTMLParser
from html import unescape

from mcp.server.fastmcp import FastMCP

HOME = Path.home()
BASE = HOME / "brain" / "teach"
ASYNC = str(HOME / "teach-engine" / "run_teach_async.sh")
REGISTRY = BASE / "tracks.json"
RUN_TTL = 900  # seconds after which an orphaned .spawn.lock counts as stale

mcp = FastMCP("teach")


# ---------- helpers ----------

def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").strip().lower())
    return re.sub(r"-{2,}", "-", s).strip("-")


def _load() -> dict:
    if REGISTRY.exists():
        try:
            return json.loads(REGISTRY.read_text())
        except Exception:
            pass
    return {"bindings": {}}


def _save(d: dict) -> None:
    BASE.mkdir(parents=True, exist_ok=True)
    REGISTRY.write_text(json.dumps(d, indent=2))


def _tracks_on_disk() -> list:
    if not BASE.exists():
        return []
    return sorted(p.name for p in BASE.iterdir() if p.is_dir() and (p / "MISSION.md").exists())


def _status(slug: str) -> dict:
    p = BASE / slug / ".status.json"
    try:
        return json.loads(p.read_text()) if p.exists() else {}
    except Exception:
        return {}


def _claim(slug: str, mode: str) -> bool:
    """Atomically claim the track for one background job (O_CREAT|O_EXCL lock file),
    then mark it running. False = another job holds it. The async runner removes the
    lock when it exits; a lock older than RUN_TTL is treated as orphaned and retaken."""
    d = BASE / slug
    d.mkdir(parents=True, exist_ok=True)
    lock = d / ".spawn.lock"
    for _ in range(2):
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > RUN_TTL:
                    lock.unlink()
                    continue
            except FileNotFoundError:
                continue
            return False
        os.write(fd, str(int(time.time())).encode())
        os.close(fd)
        (d / ".status.json").write_text(
            json.dumps({"state": "running", "mode": mode, "epoch": int(time.time())}))
        return True
    return False


def _spawn(mode: str, slug: str, payload_text=None) -> bool:
    """Claim the track, then launch the detached engine job (survives MCP reconnects
    via a new session). Returns False if the track is already busy."""
    if not _claim(slug, mode):
        return False
    args = ["setsid", "bash", ASYNC, mode, slug]
    try:
        if payload_text is not None:
            tf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False)
            tf.write(payload_text)
            tf.close()
            args.append(tf.name)
        subprocess.Popen(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        (BASE / slug / ".spawn.lock").unlink(missing_ok=True)
        (BASE / slug / ".status.json").write_text(json.dumps(
            {"state": "error", "mode": mode, "epoch": int(time.time()), "error": f"spawn failed: {e}"}))
        raise
    return True


# ---------- engine tools (async: return immediately, push when done) ----------

@mcp.tool()
def onboard_track(name: str, mission: str = "") -> str:
    """Create a new learning track in the BACKGROUND. `name` is the track's human
    name (e.g. 'Linear Algebra'); `mission` is the gathered goal/why/success/
    constraints. Returns immediately; a confirmation + next step is posted to the
    topic when the track is ready (~1-2 min)."""
    slug = _slug(name)
    if not slug:
        return "ERROR: could not derive a valid slug from that name."
    if (BASE / slug / "MISSION.md").exists():
        return f"Track '{slug}' already exists: open its topic, or pick a different name."
    if not _spawn("onboard", slug, json.dumps({"name": name, "mission": mission})):
        return f"Already setting up '{slug}'; it'll confirm here shortly."
    return (f"🛠️ Setting up track '{slug}' in the background (~1-2 min). "
            f"I'll confirm here with the next step when it's ready, no need to wait.")


@mcp.tool()
def create_next_lesson(track: str, difficulty: str = "") -> str:
    """Generate the next lesson for `track` in the BACKGROUND. Optional `difficulty`:
    'too easy' | 'good' | 'too hard'. Returns immediately; the lesson link is posted
    to this topic when ready (~5 min). Do NOT wait or call repeatedly."""
    slug = _slug(track)
    if not (BASE / slug / "MISSION.md").exists():
        return f"ERROR: no track '{slug}'. Onboard it first."
    if not _spawn("lesson", slug, (difficulty or None)):
        return f"A lesson for '{slug}' is already generating; it'll post here shortly. Hang tight."
    return (f"🛠️ Generating your next lesson for '{slug}' in the background (~5 min). "
            f"I'll post the link right here when it's ready; you can put your phone down.")


@mcp.tool()
def record_feedback(track: str, results: str) -> str:
    """Record the learner's pasted Copy-results / answers for `track` in the
    BACKGROUND, updating learning-records so the next lesson calibrates. Returns
    immediately; confirms in the topic when saved."""
    slug = _slug(track)
    if not (BASE / slug / "MISSION.md").exists():
        return f"ERROR: no track '{slug}'."
    if not _spawn("feedback", slug, results):
        return f"Busy with '{slug}' right now; try again in a moment."
    return f"📝 Recording your progress for '{slug}' in the background; I'll confirm here shortly."


@mcp.tool()
def lesson_status(track: str) -> str:
    """Check whether a background generation for `track` is still running, done, or errored."""
    slug = _slug(track)
    s = _status(slug)
    st = s.get("state")
    if st == "running":
        return f"Still generating '{slug}' ({int(time.time() - s.get('epoch', 0))}s so far), hang on."
    if st == "done":
        return f"Done: {s.get('url', '(no url)')}"
    if st == "error":
        return f"Last run errored: {s.get('error', '')[:200]}. Ask me to retry."
    return f"No recent generation for '{slug}'."


# ---------- registry tools ----------

@mcp.tool()
def bind_topic(thread_id: str, track: str) -> str:
    """Operator/maintenance use; the chat agent does not call this. Bind a Telegram
    topic (thread_id) to a track slug in tracks.json, so background jobs post their
    results into that topic. Part of wiring a new track topic (see the README)."""
    slug = _slug(track)
    if not (BASE / slug / "MISSION.md").exists():
        return f"ERROR: no track '{slug}' to bind."
    d = _load()
    d.setdefault("bindings", {})[str(thread_id)] = {
        "track": slug,
        "name": track,
        "created": datetime.datetime.now().isoformat(timespec="seconds"),
    }
    _save(d)
    return f"Bound this topic (thread {thread_id}) to track '{slug}'."


@mcp.tool()
def get_track(thread_id: str) -> str:
    """Resolve which track a Telegram topic (thread_id) is bound to in tracks.json.
    If unbound, lists tracks that have no topic yet (the operator wires those)."""
    d = _load()
    b = d.get("bindings", {}).get(str(thread_id))
    if b:
        return f"track={b['track']} (name: {b.get('name', '')})"
    bound = {v["track"] for v in d.get("bindings", {}).values()}
    pending = [t for t in _tracks_on_disk() if t not in bound]
    if pending:
        return ("UNBOUND topic. Tracks with no topic yet: " + ", ".join(pending) +
                ". This topic needs its one-time wiring by the operator; do not bind it yourself.")
    return "UNBOUND topic and no pending tracks. Onboard a track in the General topic first."


@mcp.tool()
def list_tracks() -> str:
    """List all learning tracks and their topic bindings."""
    d = _load()
    by_track = {v["track"]: tid for tid, v in d.get("bindings", {}).items()}
    lines = [f"- {t}" + (f" -> topic {by_track[t]}" if t in by_track else " (no topic yet)")
             for t in _tracks_on_disk()]
    return "Tracks:\n" + ("\n".join(lines) if lines else "(none yet)")


# ---------- content-read tools (let the chat agent READ the real lessons/cards) ----------

class _TextExtractor(HTMLParser):
    """Strip a lesson/reference HTML card down to readable text (drops style/script)."""
    SKIP = {"style", "script", "head", "title"}
    BLOCK = {"p", "h1", "h2", "h3", "h4", "li", "div", "section", "tr", "summary", "label", "br"}

    def __init__(self):
        super().__init__()
        self.parts = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self._skip += 1
        elif tag in self.BLOCK:
            self.parts.append("\n")
            if tag == "li":
                self.parts.append("- ")

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        elif tag in self.BLOCK:
            self.parts.append("\n")

    def handle_data(self, data):
        if self._skip:
            return
        t = data.strip()
        if t:
            self.parts.append(t + " ")


def _html_to_text(html: str) -> str:
    p = _TextExtractor()
    try:
        p.feed(html)
    except Exception:
        pass
    text = unescape("".join(p.parts))
    out, blanks = [], 0
    for raw in text.splitlines():
        ln = re.sub(r"[ \t]+", " ", raw).strip()
        if ln:
            out.append(ln)
            blanks = 0
        else:
            blanks += 1
            if blanks == 1:
                out.append("")
    return "\n".join(out).strip()


def _content_files(d: Path) -> list:
    files = []
    for sub in ("lessons", "reference"):
        sd = d / sub
        if sd.exists():
            files += sorted(sd.glob("*.html"))
    return files


@mcp.tool()
def list_lessons(track: str) -> str:
    """List the lessons and reference cards that exist on disk for `track`. Call this
    before answering any question about a specific lesson's or card's content, then read
    the one you need with read_lesson."""
    slug = _slug(track)
    d = BASE / slug
    if not (d / "MISSION.md").exists():
        return f"ERROR: no track '{slug}'."
    lessons = sorted(p.name for p in (d / "lessons").glob("*.html")) if (d / "lessons").exists() else []
    refs = sorted(p.name for p in (d / "reference").glob("*.html")) if (d / "reference").exists() else []
    lines = ["Lessons:"] + ([f"  - {n}" for n in lessons] or ["  (none)"])
    lines += ["Reference cards:"] + ([f"  - {n}" for n in refs] or ["  (none)"])
    lines.append("")
    lines.append("Read any with read_lesson(track, which) -- `which` may be a number "
                 "('2'/'0002'), a name fragment ('eigen'), or a filename.")
    return "\n".join(lines)


@mcp.tool()
def read_lesson(track: str, which: str) -> str:
    """Read the ACTUAL content of a lesson or reference card for `track`, so you answer
    from the real text instead of memory. `which` may be a lesson number ('2'/'0002'),
    a name fragment ('eigen'), or a filename; searches lessons/ then reference/.
    ALWAYS call this before describing a lesson's or card's steps/content -- never
    reconstruct them. Returns the readable text (truncated if very long)."""
    slug = _slug(track)
    d = BASE / slug
    if not (d / "MISSION.md").exists():
        return f"ERROR: no track '{slug}'."
    files = _content_files(d)
    if not files:
        return f"No lesson or reference files found for '{slug}'."
    q = (which or "").strip().lower()
    qh = q.replace(" ", "-")
    target = None
    num = re.sub(r"[^0-9]", "", q)
    if num:
        padded = num.zfill(4)
        target = next((c for c in files if c.name.startswith(padded)), None)
    if target is None and q:
        target = next((c for c in files if q in c.stem.lower() or qh in c.stem.lower()), None)
    if target is None:
        names = ", ".join(c.name for c in files)
        return f"Couldn't match '{which}' for '{slug}'. Available: {names}."
    try:
        html = target.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"ERROR reading {target.name}: {e}"
    text = _html_to_text(html)
    if len(text) > 8000:
        text = text[:8000] + "\n...(truncated)"
    return f"[{target.relative_to(BASE)}]\n\n{text}"


if __name__ == "__main__":
    mcp.run()
