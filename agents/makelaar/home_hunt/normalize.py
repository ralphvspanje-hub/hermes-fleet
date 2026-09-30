"""Parse scraped strings into the typed fields `Listing` expects."""
import re
from .models import HousingType

_SOLO_HINTS = ("studio", "appartement", "apartment", "woning", "huis", "loft",
               "maisonnette", "self-contained", "zelfstandig")
_SHARED_HINTS = ("kamer", "room", "huisgenoot", "roommate", "shared", "gedeeld",
                 "hospiteren", "flatmate")
_ROOM_COUNT = re.compile(r"\d\s*-?\s*kamer")  # '3-kamer' = a whole flat's room count
_ASAP = ("per direct", "direct beschikbaar", "immediately", "available now",
         "now", "asap", "z.s.m", "zo snel mogelijk")


def parse_price(text):
    """'€ 1.250 p/m' -> 1250 ; '€950' -> 950 ; 'op aanvraag' -> None."""
    if not text:
        return None
    t = text.replace(" ", " ")
    m = re.search(r"\d[\d.\s]*", t)
    if not m:
        return None
    digits = re.sub(r"[.\s]", "", m.group(0))
    try:
        val = int(digits)
    except ValueError:
        return None
    # a parsed rent under €300 is almost certainly a mis-parse (service costs / a
    # stray number), not a real Amsterdam rent → treat the price as unknown.
    return val if val >= 300 else None


def infer_housing_type(title, description=""):
    """A 'kamer'/'room' is SHARED, unless it's a room-COUNT like '3-kamer' (a whole flat)."""
    t = f"{title} {description}".lower()
    if any(h in t for h in _SHARED_HINTS) and not _ROOM_COUNT.search(t):
        return HousingType.SHARED
    if any(h in t for h in _SOLO_HINTS):
        return HousingType.SOLO
    return HousingType.UNKNOWN


def parse_available_from(text):
    """Normalize move-in: immediate markers -> 'asap'; else the trimmed string; '' -> None."""
    if not text or not text.strip():
        return None
    t = text.strip()
    if any(k in t.lower() for k in _ASAP):
        return "asap"
    return t
