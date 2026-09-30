from home_hunt.store import Store
from home_hunt.classify import classify
from home_hunt.config import Config
from home_hunt.models import Listing, HousingType
import importlib.util
from pathlib import Path

# load engine/homehunt_mcp.py as a module
_spec = importlib.util.spec_from_file_location(
    "homehunt_mcp", Path(__file__).parent.parent / "engine" / "homehunt_mcp.py")
mcpmod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mcpmod)


def _dec(sid, **kw):
    base = dict(source="example", source_id=sid, url="https://x/" + sid, title="Studio " + sid,
                description="", price_eur=1200, housing_type=HousingType.SOLO,
                area="De Pijp", registration=True)
    base.update(kw)
    return classify(Listing(**base), Config())


def test_recent_listings_core_formats_shown(tmp_path):
    s = Store(str(tmp_path / "s.sqlite"))
    s.record(_dec("1"), ts="2026-06-25T09:00")
    s.record(_dec("2", is_sublet=True), ts="2026-06-25T10:00")   # DROP, excluded
    out = mcpmod.recent_listings_core(s, limit=10)
    assert "Studio 1" in out and "https://x/1" in out
    assert "Studio 2" not in out                                   # dropped not shown


def test_mark_listing_core_validates_status(tmp_path):
    s = Store(str(tmp_path / "s.sqlite"))
    s.record(_dec("1"))
    assert "interested" in mcpmod.mark_listing_core(s, "example", "1", "interested").lower()
    assert s.status("example", "1") == "interested"
    # an unknown status is rejected (no arbitrary writes)
    assert "ERROR" in mcpmod.mark_listing_core(s, "example", "1", "delete; drop table")
    assert s.status("example", "1") == "interested"                  # unchanged


def test_listing_detail_core_found_and_missing(tmp_path):
    s = Store(str(tmp_path / "s.sqlite"))
    s.record(_dec("7"))
    found = mcpmod.listing_detail_core(s, "example", "7")
    assert "Studio 7" in found and "https://x/7" in found
    assert "No listing" in mcpmod.listing_detail_core(s, "example", "nope")


def test_recent_listings_core_empty_and_include_dismissed(tmp_path):
    s = Store(str(tmp_path / "s.sqlite"))
    assert "No current listings" in mcpmod.recent_listings_core(s)
    s.record(_dec("1"))
    s.mark("example", "1", "dismissed")
    assert "Studio 1" not in mcpmod.recent_listings_core(s)                 # hidden by default
    assert "Studio 1" in mcpmod.recent_listings_core(s, include_dismissed=True)


def test_mark_listing_core_missing_listing(tmp_path):
    s = Store(str(tmp_path / "s.sqlite"))
    assert "ERROR" in mcpmod.mark_listing_core(s, "example", "ghost", "interested")


def test_fmt_tolerates_null_columns(tmp_path):
    s = Store(str(tmp_path / "s.sqlite"))
    s.record(_dec("1"))
    s.conn.execute("UPDATE seen SET score=NULL, title=NULL, url=NULL WHERE source_id='1'")
    s.conn.commit()
    out = mcpmod.listing_detail_core(s, "example", "1")
    assert "None" not in out          # NULL columns render as safe placeholders, not 'None'


def test_spend_status_core(tmp_path):
    from home_hunt.budget import SpendGuard
    g = SpendGuard(str(tmp_path / "b.sqlite"), monthly_cap_eur=50)
    g.record("2026-06", 2.0)
    out = mcpmod.spend_status_core(g, "2026-06")
    assert "2.0" in out or "2.00" in out
    assert "50" in out


def test_month_defaults_to_current_month(monkeypatch):
    import datetime
    monkeypatch.delenv("HOME_HUNT_MONTH", raising=False)
    assert mcpmod._month() == datetime.date.today().strftime("%Y-%m")
    monkeypatch.setenv("HOME_HUNT_MONTH", "2030-01")
    assert mcpmod._month() == "2030-01"
