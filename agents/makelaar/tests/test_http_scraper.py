from home_hunt.sources.http import HtmlScraper
from home_hunt.models import Listing, HousingType

_HTML = """
<html><body>
  <div class="card"><a href="/l/1">Studio De Pijp</a><span class="price">€ 1.250</span></div>
  <div class="card"><a href="/l/2">Kamer Oost</a><span class="price">€ 800</span></div>
</body></html>
"""


class _Demo(HtmlScraper):
    name = "demo"
    search_url = "https://example.test/search"
    base_url = "https://example.test"

    def select_cards(self, soup):
        return soup.select("div.card")

    def card_to_listing(self, card):
        a = card.select_one("a")
        return Listing(
            source=self.name, source_id=a["href"].rsplit("/", 1)[-1],
            url=self.base_url + a["href"], title=a.get_text(strip=True),
            description="", price_eur=int(card.select_one(".price").get_text()
                                          .replace("€", "").replace(".", "").strip()),
            housing_type=HousingType.UNKNOWN, area="",
        )


def test_parse_uses_injected_html():
    src = _Demo(fetcher=lambda url: _HTML)
    listings = src.fetch()
    assert len(listings) == 2
    assert listings[0].source_id == "1"
    assert listings[0].url == "https://example.test/l/1"
    assert listings[0].price_eur == 1250


def test_card_returning_none_is_skipped():
    class _Skip(_Demo):
        def card_to_listing(self, card):
            return None
    assert _Skip(fetcher=lambda url: _HTML).fetch() == []
