from home_hunt.models import Listing, HousingType
from home_hunt.config import Config
from home_hunt.scoring import score

CFG = Config()


def _l(**kw):
    base = dict(source="t", source_id="1", url="u", title="", description="",
                price_eur=1100, housing_type=HousingType.SOLO, area="Jordaan",
                registration=True)
    base.update(kw)
    return Listing(**base)


def test_bullseye_solo_middenhuur_scores_high():
    pts, why = score(_l(), CFG)
    assert pts >= 80
    assert "solo" in why


def test_solo_beats_shared_all_else_equal():
    solo, _ = score(_l(housing_type=HousingType.SOLO), CFG)
    shared, _ = score(_l(housing_type=HousingType.SHARED, price_eur=950), CFG)
    assert solo > shared


def test_unknown_area_still_scores():
    pts, _ = score(_l(area="Nowhere"), CFG)
    assert 0 < pts <= 100
