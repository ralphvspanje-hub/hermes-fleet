from home_hunt.store import Store
from home_hunt.classify import classify
from home_hunt.config import Config
from home_hunt.models import Listing, HousingType, Verdict


def _dec(source_id, **kw):
    base = dict(source="example", source_id=source_id, url="https://x/" + source_id,
                title="Studio " + source_id, description="", price_eur=1200,
                housing_type=HousingType.SOLO, area="De Pijp", registration=True)
    base.update(kw)
    return classify(Listing(**base), Config())


def test_record_persists_listing_fields_and_get(tmp_path):
    s = Store(str(tmp_path / "s.sqlite"))
    s.record(_dec("1"), ts="2026-06-25")
    row = s.get("example", "1")
    assert row["title"] == "Studio 1"
    assert row["url"] == "https://x/1"
    assert row["price_eur"] == 1200
    assert row["area"] == "De Pijp"
    assert row["verdict"] == Verdict.SHOW.value
    assert row["status"] == "new"
    s.close()


def test_recent_default_and_empty_verdicts_never_surface_drop(tmp_path):
    s = Store(str(tmp_path / "s.sqlite"))
    s.record(_dec("1"), ts="t1")                       # SHOW
    s.record(_dec("2", is_sublet=True), ts="t2")       # DROP
    # both the default (verdicts omitted) and an explicit empty tuple stay safe
    assert [r["source_id"] for r in s.recent()] == ["1"]
    assert "2" not in [r["source_id"] for r in s.recent(verdicts=())]
    s.close()


def test_recent_keeps_null_status_rows_when_excluding(tmp_path):
    s = Store(str(tmp_path / "s.sqlite"))
    s.record(_dec("1"), ts="t1")
    s.conn.execute("UPDATE seen SET status=NULL WHERE source_id='1'")   # simulate a migration gap
    s.conn.commit()
    ids = [r["source_id"] for r in s.recent(exclude_status=("dismissed",))]
    assert "1" in ids                                  # NULL status not silently dropped
    s.close()


def test_recent_returns_shown_newest_first_and_respects_status(tmp_path):
    s = Store(str(tmp_path / "s.sqlite"))
    s.record(_dec("1"), ts="2026-06-25T09:00")
    s.record(_dec("2"), ts="2026-06-25T10:00")
    s.record(_dec("3", is_sublet=True), ts="2026-06-25T11:00")   # DROP
    recent = s.recent(verdicts=(Verdict.SHOW.value, Verdict.FLAG.value), limit=10)
    ids = [r["source_id"] for r in recent]
    assert ids == ["2", "1"]                  # newest first, the DROP excluded
    s.mark("example", "2", "dismissed")
    ids2 = [r["source_id"] for r in s.recent(exclude_status=("dismissed",))]
    assert ids2 == ["1"]                       # dismissed hidden
    s.close()
