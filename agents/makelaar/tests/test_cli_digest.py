from home_hunt.cli import digest_from_store
from home_hunt.store import Store
from home_hunt.classify import classify
from home_hunt.config import Config
from home_hunt.models import Listing, HousingType


def _dec(sid, score_area="Jordaan"):
    return classify(Listing(source="example", source_id=sid, url="u" + sid, title="Studio " + sid,
                    description="", price_eur=1100, housing_type=HousingType.SOLO,
                    area=score_area, registration=True), Config())


def test_digest_from_store_skips_dismissed(tmp_path):
    s = Store(str(tmp_path / "s.sqlite"))
    s.record(_dec("1", "Centrum"), ts="2026-06-25T09:00")
    s.record(_dec("2", "Jordaan"), ts="2026-06-25T10:00")
    s.mark("example", "1", "dismissed")
    text = digest_from_store(s)
    assert "Studio 2" in text
    assert "Studio 1" not in text          # dismissed excluded
    s.close()


def test_digest_from_store_ranks_by_score_desc(tmp_path):
    s = Store(str(tmp_path / "s.sqlite"))
    # Centrum (GREAT) scores lower than Jordaan (BULLSEYE); record low-score first
    s.record(_dec("low", "Centrum"), ts="2026-06-25T11:00")
    s.record(_dec("high", "Jordaan"), ts="2026-06-25T09:00")
    text = digest_from_store(s)
    assert text.index("Studio high") < text.index("Studio low")   # higher score listed first
    s.close()
