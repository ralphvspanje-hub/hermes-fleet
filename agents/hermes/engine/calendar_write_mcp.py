#!/usr/bin/env python3
"""Minimal stdio MCP server exposing calendar CREATE + UPDATE only (no delete).

Wraps the gogcli CLI with a write-scoped token bucket. gogcli's own MCP exposes the
calendar as read-only, so this fills the write gap with a tightly-scoped surface:
two tools, no delete, no other Google service. The chat agent calls these; it never
gets a shell. Newline-delimited JSON-RPC 2.0 over stdin/stdout (MCP stdio transport).

Deliberately NO delete tool: a prompt-injected or confused agent can at worst add or
move an event, which is visible and reversible. A deleted event is neither.

Environment:
  GOG_ACCOUNT        Google account gogcli is authorized for (a DEDICATED automation
                     account, never your main one). Required.
  CALENDAR_ID        Calendar to write to (default: primary).
  GOG_BIN            Path to the gog binary (default: gog on PATH, else ~/.local/bin/gog).
  GOG_WRITE_CLIENT   gogcli token bucket holding the write `calendar` scope (default: rw).
                     Keep the read-only bucket separate so unattended readers hold no
                     write power.

Argument hardening: every value reaches gog as `--flag=value`, so a value starting with
"-" stays a value and can never become a new flag; event ids must match a strict
pattern; non-string values are rejected. The agent's arguments are untrusted input.
"""
import json
import os
import re
import shutil
import subprocess
import sys

ACCOUNT = os.environ.get("GOG_ACCOUNT", "")
GOG = os.environ.get("GOG_BIN") or shutil.which("gog") or os.path.expanduser("~/.local/bin/gog")
CLIENT = os.environ.get("GOG_WRITE_CLIENT", "rw")
CALENDAR = os.environ.get("CALENDAR_ID", "primary")
# Argv prefix for gog; a list so tests can point it at a fake binary via an interpreter.
GOG_CMD = [GOG]

EVENT_ID_RE = re.compile(r"[A-Za-z0-9_]{1,1024}")

TOOLS = [
    {
        "name": "calendar_create_event",
        "description": (
            "Create a new event on the user's Google Calendar. Times are RFC3339 with the "
            "user's local timezone offset, e.g. 2026-06-27T09:00:00+00:00 (mind daylight "
            "saving). ALWAYS check the slot first with the calendar_events read tool; create "
            "immediately if it's free, otherwise ask the user before creating. "
            "This tool cannot delete events."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Event title"},
                "start": {"type": "string", "description": "Start time, RFC3339 with offset. For an all-day event use YYYY-MM-DD and set all_day=true."},
                "end": {"type": "string", "description": "End time, RFC3339 with offset. For all-day, use the day AFTER as the date."},
                "description": {"type": "string", "description": "Optional notes"},
                "location": {"type": "string", "description": "Optional location"},
                "all_day": {"type": "boolean", "description": "All-day event (use date-only start/end)"},
            },
            "required": ["summary", "start", "end"],
        },
    },
    {
        "name": "calendar_update_event",
        "description": (
            "Update or move an existing event on the user's Google Calendar, identified by "
            "event_id (get the id from the calendar_events read tool). Only set the fields "
            "you want to change. Times are RFC3339 with offset. This tool cannot delete events."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "string", "description": "Google Calendar event id (from calendar_events)"},
                "start": {"type": "string", "description": "New start time, RFC3339 with offset"},
                "end": {"type": "string", "description": "New end time, RFC3339 with offset"},
                "summary": {"type": "string", "description": "New title"},
                "description": {"type": "string", "description": "New notes"},
                "location": {"type": "string", "description": "New location"},
            },
            "required": ["event_id"],
        },
    },
]


class BadArgs(ValueError):
    """An argument from the agent failed validation."""


def _str_arg(a, key, required=False):
    v = a.get(key)
    if v is None or v == "":
        if required:
            raise BadArgs(f"missing required argument: {key}")
        return None
    if not isinstance(v, str):
        raise BadArgs(f"{key} must be a string")
    if chr(0) in v or (chr(10) in v and key != "description"):
        raise BadArgs(f"{key} contains an invalid character")
    return v


def run_gog(args):
    if not ACCOUNT:
        return False, "GOG_ACCOUNT is not set: configure the calendar-write MCP's environment."
    if CALENDAR.startswith("-"):
        return False, "CALENDAR_ID must not start with '-'."
    cmd = GOG_CMD + [f"--account={ACCOUNT}", f"--client={CLIENT}"] + args + ["--json", "--no-input"]
    env = dict(os.environ)
    env.pop("GOG_READONLY", None)  # this is the write path; never run read-only
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
    except Exception as e:
        return False, f"failed to run gog: {e}"
    out, err = (p.stdout or "").strip(), (p.stderr or "").strip()
    if p.returncode != 0:
        return False, (err or out or f"gog exited {p.returncode}")
    return True, (out or "done")


def tool_create(a):
    summary = _str_arg(a, "summary", required=True)
    start = _str_arg(a, "start", required=True)
    end = _str_arg(a, "end", required=True)
    args = ["calendar", "create", CALENDAR, f"--summary={summary}", f"--from={start}", f"--to={end}"]
    for key in ("description", "location"):
        v = _str_arg(a, key)
        if v is not None:
            args.append(f"--{key}={v}")
    all_day = a.get("all_day", False)
    if not isinstance(all_day, bool):
        raise BadArgs("all_day must be a boolean")
    if all_day:
        args.append("--all-day")
    return run_gog(args)


def tool_update(a):
    event_id = a.get("event_id")
    if not isinstance(event_id, str) or not EVENT_ID_RE.fullmatch(event_id):
        raise BadArgs("event_id must be a Google Calendar event id (letters, digits, underscore)")
    args = ["calendar", "update", CALENDAR, event_id]
    changed = False
    for key, flag in (("start", "--from"), ("end", "--to"), ("summary", "--summary"),
                      ("description", "--description"), ("location", "--location")):
        v = _str_arg(a, key)
        if v is not None:
            args.append(f"{flag}={v}")
            changed = True
    if not changed:
        return False, "Nothing to update: provide at least one field to change (start/end/summary/...)."
    return run_gog(args)


# Create and update only. There is intentionally no delete handler.
HANDLERS = {"calendar_create_event": tool_create, "calendar_update_event": tool_update}


def send(msg):
    sys.stdout.write(json.dumps(msg) + "\n")
    sys.stdout.flush()


def main():
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue
        method = req.get("method")
        mid = req.get("id")
        if method == "initialize":
            send({"jsonrpc": "2.0", "id": mid, "result": {
                "protocolVersion": (req.get("params") or {}).get("protocolVersion", "2024-11-05"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "calendar-write", "version": "1.0.0"},
            }})
        elif method == "notifications/initialized":
            continue  # notification, no reply
        elif method == "ping":
            send({"jsonrpc": "2.0", "id": mid, "result": {}})
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            params = req.get("params") or {}
            name = params.get("name")
            args = params.get("arguments") or {}
            handler = HANDLERS.get(name)
            if not handler:
                send({"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True}})
                continue
            try:
                ok, text = handler(args)
            except BadArgs as e:
                ok, text = False, f"invalid arguments: {e}"
            except Exception as e:
                ok, text = False, f"error: {e}"
            send({"jsonrpc": "2.0", "id": mid, "result": {"content": [{"type": "text", "text": text[:4000]}], "isError": not ok}})
        elif mid is not None:
            send({"jsonrpc": "2.0", "id": mid, "error": {"code": -32601, "message": f"Method not found: {method}"}})


if __name__ == "__main__":
    main()
