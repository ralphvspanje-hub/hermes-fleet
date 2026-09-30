"""Generic alert-email parser: extract every external listing link + the nearest
price text. Used for senders without a bespoke parser. EmailAlerts builds one
concrete instance per known sender (passing source + sender substrings)."""
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from .base import EmailParser
from .. import normalize
from ..models import Listing

# digits + dot thousands-separators only (NO internal whitespace) so a price never
# bleeds into a following postcode/floor-area in flattened email text.
_PRICE_NEAR = re.compile(r"€\s*\d[\d.]*", re.IGNORECASE)
_SKIP = ("unsubscribe", "afmelden", "privacy", "mailto:", "facebook", "twitter",
         "instagram", "linkedin", "/login", "/account", "preferences",
         "disclaimer", "voorwaarden", "/cookie", "/contact", "/over-ons")


class GenericEmail(EmailParser):
    def __init__(self, source, senders):
        self.name = source
        self.source = source
        self.senders = tuple(senders)

    def parse(self, html, subject=""):
        soup = BeautifulSoup(html or "", "html.parser")
        out, seen = [], set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            low = href.lower()
            if not low.startswith("http") or any(s in low for s in _SKIP):
                continue
            block = a.find_parent(["div", "td", "tr", "li"]) or a
            text = block.get_text(" ", strip=True) if hasattr(block, "get_text") else ""
            m = _PRICE_NEAR.search(text)
            price = normalize.parse_price(m.group(0) if m else "")
            if price is None:
                continue          # no price → boilerplate (disclaimer / homepage / click-tracker), not a listing
            # key on path+query (not just the slug): distinct listings can share a path
            # (e.g. click-trackers /ls/click?upn=<unique>) and must not collapse into one.
            p = urlparse(href)
            source_id = (p.path + ("?" + p.query if p.query else "")).rstrip("/") or href
            if source_id in seen:
                continue
            seen.add(source_id)
            title = a.get_text(strip=True) or source_id
            out.append(Listing(
                source=self.source, source_id=source_id, url=href, title=title,
                description=title, price_eur=price,
                housing_type=normalize.infer_housing_type(title, text),
                area=None, registration=None))
        return out
