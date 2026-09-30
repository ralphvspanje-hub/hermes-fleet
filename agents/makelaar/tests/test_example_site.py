from pathlib import Path
from home_hunt.sources.example_site import ExampleSite
from home_hunt.sources.base import available_sources
from home_hunt.models import HousingType

FIX = Path(__file__).parent / "fixtures" / "example_search.html"


def test_parses_four_listings():
    listings = ExampleSite().parse(FIX.read_text(encoding="utf-8"))
    assert len(listings) == 4
    assert all(l.price_eur > 0 for l in listings)
    assert all(l.url.startswith("https://example.com/") for l in listings)


def test_fields_mapped_from_card():
    first = ExampleSite().parse(FIX.read_text(encoding="utf-8"))[0]
    assert first.source == "example"
    assert first.source_id == "1"
    assert first.price_eur == 1250
    assert first.area == "De Pijp"
    assert first.housing_type == HousingType.SOLO


def test_relative_href_resolved_and_id_drops_query():
    rel = ExampleSite().parse(FIX.read_text(encoding="utf-8"))[3]
    assert rel.url == "https://example.com/listing/7?ref=mail"
    assert rel.source_id == "7"


def test_fetch_uses_injected_fetcher_and_is_registered():
    src = ExampleSite(fetcher=lambda url: FIX.read_text(encoding="utf-8"))
    assert len(src.fetch()) == 4
    assert "example" in available_sources()
