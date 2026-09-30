from home_hunt.sources.base import Source, register, get_enabled, available_sources
from home_hunt.models import Listing, HousingType
from home_hunt.settings import Settings


@register
class _FakeSource(Source):
    name = "fake"

    def fetch(self):
        return [Listing(source="fake", source_id="1", url="u", title="Studio",
                        description="", price_eur=1000, housing_type=HousingType.SOLO,
                        area="De Pijp")]


def test_registry_and_enabled():
    assert "fake" in available_sources()
    s = Settings(enabled_sources=("fake",))
    enabled = get_enabled(s)
    assert len(enabled) == 1 and enabled[0].name == "fake"
    listings = enabled[0].fetch()
    assert listings[0].source_id == "1"


def test_unknown_enabled_name_is_skipped():
    s = Settings(enabled_sources=("fake", "does_not_exist"))
    enabled = get_enabled(s)
    assert [e.name for e in enabled] == ["fake"]
