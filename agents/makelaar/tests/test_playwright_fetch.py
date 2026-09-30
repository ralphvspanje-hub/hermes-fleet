from pathlib import Path
from home_hunt.sources.playwright_fetch import ExampleSiteLive
from home_hunt.sources.base import available_sources

FIX = (Path(__file__).parent / "fixtures" / "example_search.html").read_text(encoding="utf-8")


def test_example_live_uses_renderer_and_reuses_parser():
    # inject a fake renderer returning the saved example fixture (no real browser)
    src = ExampleSiteLive(renderer=lambda url, settings=None: FIX)
    listings = src.fetch()
    assert len(listings) == 4
    assert listings[0].source == "example"          # listing source = the website


def test_example_live_registry_name_distinct_from_source():
    # registered under its own key so it can be enabled separately from the static
    # example scraper, while the listings it emits still carry source="example".
    assert "example_live" in available_sources()
    assert ExampleSiteLive(renderer=lambda url, settings=None: FIX).name == "example_live"
