from home_hunt.models import Listing, HousingType
from home_hunt.config import Config
from home_hunt.filters import hard_drop_reason

CFG = Config()
CFG_50K = Config(income_eur=50000)   # an example income, to exercise the filter


def _l(**kw):
    base = dict(source="t", source_id="1", url="u", title="", description="",
                price_eur=900, housing_type=HousingType.SOLO, area="De Pijp")
    base.update(kw)
    return Listing(**base)


def test_keeps_a_clean_listing():
    assert hard_drop_reason(_l(), CFG) is None


def test_drops_no_registration_and_sublet_and_woningruil():
    assert hard_drop_reason(_l(registration=False), CFG) == "no registration"
    assert hard_drop_reason(_l(description="inschrijven niet mogelijk"), CFG) == "no registration"
    assert hard_drop_reason(_l(is_sublet=True), CFG) == "sublet/onderhuur"
    assert hard_drop_reason(_l(description="Woningruil aangeboden"), CFG) == "woningruil (home-swap)"


def test_drops_solo_over_budget():
    assert hard_drop_reason(_l(housing_type=HousingType.SOLO, price_eur=1600), CFG) == "solo over €1500"


def test_shared_off_by_default_but_optional():
    # shared is filtered out entirely by default (no shared spam)
    assert "shared" in (hard_drop_reason(_l(housing_type=HousingType.SHARED, price_eur=950), CFG) or "").lower()
    # when explicitly allowed, the strict ≤€1000 ceiling applies
    cfg = Config(allow_shared=True)
    assert hard_drop_reason(_l(housing_type=HousingType.SHARED, price_eur=1100), cfg) == "shared over €1000"
    assert hard_drop_reason(_l(housing_type=HousingType.SHARED, price_eur=950), cfg) is None


def test_excludes_wrong_city_from_title_when_area_missing():
    # city only in the title (mashed into a number), area None
    l = _l(area=None, title="Voorbeeldlaan, Hoofddorp60 m2 Furnished Apartment")
    assert hard_drop_reason(l, CFG) == "outside target area"


def test_drops_geo_and_income_and_exclusions():
    assert hard_drop_reason(_l(area="Bijlmer"), CFG) == "outside target area"
    assert hard_drop_reason(_l(description="Maximaal inkomen €48.000"), CFG_50K) == "max income €48000 < €50000"


def test_household_exclusions_off_by_default():
    assert CFG.exclude_household_tags == ()
    assert hard_drop_reason(_l(description="voor twee vrouwen"), CFG) is None
    assert hard_drop_reason(_l(description="students only"), CFG) is None


def test_household_exclusions_opt_in():
    cfg = Config(exclude_household_tags=("women_only", "student_only"))
    assert hard_drop_reason(_l(description="voor twee vrouwen"), cfg) == "women-only"
    assert hard_drop_reason(_l(description="students only"), cfg) == "student-only house"
    only_women = Config(exclude_household_tags=("women_only",))
    assert hard_drop_reason(_l(description="students only"), only_women) is None
    assert hard_drop_reason(_l(description="x"), Config(exclude_household_tags=("unknown",))) is None


def test_income_unit_aware():
    # monthly cap that annualizes to >= the user's income → NOT dropped (they qualify)
    assert hard_drop_reason(_l(description="inkomen tot 5000 per maand"), CFG_50K) is None
    # monthly cap that annualizes below the user's income → dropped
    assert hard_drop_reason(_l(description="inkomen tot 3000 per maand"), CFG_50K) == "max income €36000 < €50000"


def test_income_filter_disabled_when_income_zero():
    # default income_eur=0 means "not set": never drop on a max-income cap
    assert CFG.income_eur == 0
    assert hard_drop_reason(_l(description="Maximaal inkomen €48.000"), CFG) is None
    assert hard_drop_reason(_l(max_income_eur=30000), CFG) is None
    assert hard_drop_reason(_l(max_income_eur=30000), CFG_50K) == "max income €30000 < €50000"
