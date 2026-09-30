"""Base class for cheap HTML scrapers. `fetcher` is injectable so tests pass HTML
directly (no network). Live runs lazily import `requests`."""
from bs4 import BeautifulSoup
from .base import Source


class HtmlScraper(Source):
    name = "html"
    search_url = ""
    base_url = ""

    def __init__(self, settings=None, fetcher=None):
        super().__init__(settings)
        self._fetch = fetcher or self._default_fetch

    def _default_fetch(self, url):
        import requests  # lazy: only needed for live runs
        headers = {"User-Agent": getattr(self.settings, "user_agent", "Mozilla/5.0"),
                   "Accept-Language": "nl-NL,nl;q=0.9,en;q=0.8"}
        timeout = getattr(self.settings, "request_timeout", 20)
        r = requests.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.text

    def fetch(self):
        return self.parse(self._fetch(self.search_url))

    def parse(self, html):
        soup = BeautifulSoup(html, "html.parser")
        out = []
        for card in self.select_cards(soup):
            try:
                listing = self.card_to_listing(card)
            except Exception:
                listing = None       # a single malformed card never kills the page
            if listing is not None:
                out.append(listing)
        return out

    # --- per-site adapters override these two ---
    def select_cards(self, soup):
        raise NotImplementedError

    def card_to_listing(self, card):
        raise NotImplementedError
