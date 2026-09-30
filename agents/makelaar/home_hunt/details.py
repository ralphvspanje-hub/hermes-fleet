"""Detail-page enrichment: for a SHOW/FLAG listing, read the full listing page and
catch dealbreakers the short alert/card text hides - a short-term lease ("voor 2
maanden"), a max-income cap, or "inschrijving niet mogelijk". The card rarely shows
these; the description does.

Only these three checks run against the fetched text - they are listing-specific
phrasings unlikely to false-trip on page boilerplate. We deliberately do NOT re-run
the sublet/woningruil checks against full-page text (a site's terms often say
"onderhuur niet toegestaan", which would falsely drop a fine listing).

`fetcher(url)->text` is injectable so tests/CI never hit the network; the default
does a cheap GET + strips tags."""
from .config import Config
from .models import Verdict
from . import phrases


def _default_fetch(url):
    import requests
    from bs4 import BeautifulSoup
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "nl-NL,nl;q=0.9"},
                     timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser").get_text(" ", strip=True)


def detail_dropper(text, config):
    """Return a drop reason found in the detail text, or None."""
    if phrases.has_unavailable(text):
        return "already reserved/rented (per page)"
    if phrases.has_temporary(text) or phrases.has_short_term(text):
        return "temporary/short-term lease (per description)"
    if phrases.has_no_registration(text):
        return "no registration (per description)"
    inc = phrases.extract_max_income(text)
    if inc is not None and config.income_eur and inc < config.income_eur:
        return f"max income €{inc} (per description)"
    return None


def refine_with_details(decisions, fetcher=None, config=None, max_fetch=25):
    config = config or Config()
    fetcher = fetcher or _default_fetch
    out, fetched = [], 0
    for d in decisions:
        if (d.verdict in (Verdict.SHOW, Verdict.FLAG) and d.listing.url and fetched < max_fetch):
            try:
                text = fetcher(d.listing.url)
            except Exception:
                text = ""                       # a failed fetch never drops a listing
            fetched += 1
            if text:
                reason = detail_dropper(text, config)
                if reason:
                    out.append(type(d)(
                        listing=d.listing, verdict=Verdict.DROP, score=0,
                        reasons=[f"detail: {reason}"] + list(d.reasons), scam_flags=d.scam_flags))
                    continue
            else:
                # Couldn't read the page - usually the site blocks our IP (large portals
                # often do). We can't confirm it's still live, so flag it loudly
                # rather than present it as a verified pick (it may already be archived).
                out.append(type(d)(
                    listing=d.listing, verdict=d.verdict, score=d.score,
                    reasons=list(d.reasons) + ["⚠️ unverified - couldn't open the page to confirm it's still available"],
                    scam_flags=d.scam_flags))
                continue
        out.append(d)
    return out
