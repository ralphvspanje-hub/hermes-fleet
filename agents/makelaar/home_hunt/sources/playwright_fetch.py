"""Tier 2: render a JS page with headless Chromium (Playwright), returning HTML,
plugged into the existing HtmlScraper parsers. `renderer` is injectable so tests
never launch a browser. Live runs need `pip install playwright && playwright install chromium`."""
from .base import register
from .example_site import ExampleSite


def render(url, settings=None):
    """Live render via Playwright (sync API). Imported lazily so this module (and
    the unit tests) never require playwright to be installed."""
    from playwright.sync_api import sync_playwright
    ua = getattr(settings, "user_agent", "Mozilla/5.0")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_context(user_agent=ua, locale="nl-NL").new_page()
        page.goto(url, wait_until="networkidle", timeout=30000)
        html = page.content()
        browser.close()
    return html


@register
class ExampleSiteLive(ExampleSite):
    """The example parser, fed by a real browser render instead of requests. Use this
    pattern for a site whose results only appear after JavaScript runs: subclass the
    site's HtmlScraper and swap fetch() for a render. It has a distinct registry name
    so it can be enabled separately, while the listings it emits still carry the
    website's source name ("example") so dedupe matches the static scraper."""
    name = "example_live"
    source_name = "example"

    def __init__(self, settings=None, renderer=None):
        super().__init__(settings)
        self._render = renderer or render

    def fetch(self):
        listings = self.parse(self._render(self.search_url, self.settings))
        for listing in listings:
            listing.source = self.source_name
        return listings
