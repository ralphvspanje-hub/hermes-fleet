"""Example HTML-scraper source: a template for adding your own site.

It parses a (synthetic) search-results page where each listing is a card like:

    <article class="listing">
      <a href="https://example.com/listing/1"><h2>Studio ...</h2></a>
      <span class="price">EUR 1.250</span>
      <span class="area">De Pijp</span>
    </article>

To add a real site: copy this file, set `name` / `search_url` / `base_url`, adapt the
two CSS-selector methods to the site's markup, capture a search page into
tests/fixtures/ and write a parser test against it, then import the module in
sources/__init__.py. Check the site's terms of use before scraping it."""
from urllib.parse import urljoin, urlparse
from .base import register
from .http import HtmlScraper
from .. import normalize
from ..models import Listing


@register
class ExampleSite(HtmlScraper):
    name = "example"
    search_url = "https://example.com/search?city=amsterdam"
    base_url = "https://example.com"

    def select_cards(self, soup):
        return soup.select("article.listing")

    def card_to_listing(self, card):
        link = card.select_one("a[href]")
        if link is None:
            return None
        href = link.get("href", "")
        url = urljoin(self.base_url + "/", href)
        source_id = urlparse(url).path.rstrip("/").rsplit("/", 1)[-1] or url
        title = link.get_text(strip=True)
        price_el = card.select_one(".price")
        area_el = card.select_one(".area")
        price_text = price_el.get_text(strip=True) if price_el else ""
        area = area_el.get_text(strip=True) if area_el else ""
        return Listing(
            source=self.name, source_id=source_id, url=url, title=title,
            description=title, price_eur=normalize.parse_price(price_text),
            housing_type=normalize.infer_housing_type(title, area),
            area=area or None, registration=None,
        )
