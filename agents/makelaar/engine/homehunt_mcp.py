#!/usr/bin/env python3
"""Home-hunt MCP - safe, high-level tools for the `makelaar` profile.

The chat agent only ever calls these tools; it never gets raw shell/file, and NO
tool ever contacts a landlord/agency, applies, or pays - they read local state,
run a scan, or update a listing's status. New SHOW/FLAG listings from a scan are
pinged to the user's chat by the engine.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # import home_hunt

from home_hunt.settings import Settings
from home_hunt.store import Store
from home_hunt.budget import SpendGuard, current_month
from home_hunt.models import Verdict

_VALID_STATUS = ("new", "interested", "contacted", "dismissed", "viewing")
_SHOWN = (Verdict.SHOW.value, Verdict.FLAG.value)


# ---------- testable core ----------

def _fmt(row):
    price = f"€{row['price_eur']}" if row.get("price_eur") else "€?"
    tag = "⚠️ " if row.get("verdict") == Verdict.FLAG.value else ""
    st = "" if row.get("status") in (None, "new") else f" [{row['status']}]"
    return (f"{tag}[{row.get('score') or 0}] {row.get('title') or '?'} - {price} - "
            f"{row.get('area') or '?'}{st}\n  {row.get('url') or ''}  ({row['source']}/{row['source_id']})")


def recent_listings_core(store, limit=20, include_dismissed=False):
    exclude = () if include_dismissed else ("dismissed",)
    rows = store.recent(verdicts=_SHOWN, exclude_status=exclude, limit=limit)
    if not rows:
        return "No current listings. Run a scan, or widen the filters."
    return "\n".join(_fmt(r) for r in rows)


def listing_detail_core(store, source, source_id):
    row = store.get(source, str(source_id))
    if not row:
        return f"No listing {source}/{source_id}."
    return _fmt(row)


def mark_listing_core(store, source, source_id, status):
    status = (status or "").strip().lower()
    if status not in _VALID_STATUS:
        return f"ERROR: status must be one of {', '.join(_VALID_STATUS)}."
    if store.get(source, str(source_id)) is None:
        return f"ERROR: no listing {source}/{source_id}."
    store.mark(source, str(source_id), status)
    return f"Marked {source}/{source_id} as '{status}'. (You always send any message yourself.)"


def spend_status_core(guard, month):
    spent = guard.spent(month)
    return f"Tier-3 spend this month ({month}): €{spent:.2f} of €{guard.cap} cap."


# ---------- FastMCP wrapper ----------

def _settings():
    return Settings.from_env()


def _store():
    return Store(_settings().db_path)


def _guard():
    return SpendGuard.from_env()


def _month():
    return current_month()   # HOME_HUNT_MONTH if set, else the current 'YYYY-MM'


if __name__ == "__main__":
    from mcp.server.fastmcp import FastMCP
    mcp = FastMCP("homehunt")

    @mcp.tool()
    def recent_listings(limit: int = 20, include_dismissed: bool = False) -> str:
        """List the current SHOW/FLAG listings (newest first). Read-only."""
        s = _store()
        try:
            return recent_listings_core(s, limit=limit, include_dismissed=include_dismissed)
        finally:
            s.close()

    @mcp.tool()
    def listing_detail(source: str, source_id: str) -> str:
        """Show one listing's details by source + id. Read-only."""
        s = _store()
        try:
            return listing_detail_core(s, source, source_id)
        finally:
            s.close()

    @mcp.tool()
    def mark_listing(source: str, source_id: str, status: str) -> str:
        """Update a listing's status: interested | contacted | dismissed | viewing | new.
        This only updates the user's local tracking - it never contacts anyone."""
        s = _store()
        try:
            return mark_listing_core(s, source, source_id, status)
        finally:
            s.close()

    @mcp.tool()
    def spend_status(month: str = "") -> str:
        """Report this month's Tier-3 (paid browse) spend against the monthly cap."""
        g = _guard()
        try:
            return spend_status_core(g, month or _month())
        finally:
            g.close()

    @mcp.tool()
    def scan_now() -> str:
        """Trigger one scan cycle now (email alerts + cheap scrape; Tier-3 only if the
        spend cap allows). New SHOW/FLAG listings are pinged to this chat as usual."""
        import subprocess
        eng = Path.home() / "home-hunt" / "engine" / "run_homehunt_scan.sh"
        if not eng.exists():
            return f"⚠️ Can't scan - the scan engine isn't installed at {eng}."
        subprocess.Popen(["setsid", "bash", str(eng)], stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return "🔎 Scanning now - I'll ping you here with anything new. No need to wait."

    mcp.run()
