"""Match score 0-100 + a one-line 'why'."""
from .models import HousingType
from . import geo, phrases

_TIER_POINTS = {geo.BULLSEYE: 30, geo.GREAT: 22, geo.FINE: 14, geo.LOWER: 6}
_DUTCH_HINTS = ("nederlands", "dutch", "wij zoeken", "gezellig", "huisgenoot")


def score(listing, config):
    pts, why = 0, []

    tier = geo.neighbourhood_tier(listing.area)
    tp = _TIER_POINTS.get(tier, 8)  # unknown area → 8
    pts += tp
    why.append(f"area+{tp}")

    if listing.housing_type == HousingType.SOLO:
        pts += 20
        why.append("solo+20")
    elif listing.housing_type == HousingType.SHARED:
        pts += 5
        why.append("shared+5")

    if listing.price_eur is not None:
        if listing.price_eur <= config.middenhuur_max_eur:
            pts += 20
            why.append(f"middenhuur €{listing.price_eur}+20")
        else:
            span = max(1, config.solo_max_eur - config.middenhuur_max_eur)
            frac = max(0.0, (config.solo_max_eur - listing.price_eur) / span)
            p = int(10 * frac)
            pts += p
            why.append(f"free-sector €{listing.price_eur}+{p}")

    text = f"{listing.title} {listing.description}"
    if listing.registration is True or phrases.has_registration_ok(text):
        pts += 10
        why.append("register+10")
    elif listing.registration is None:
        pts += 3
        why.append("register?+3")

    if any(h in (listing.description or "").lower() for h in _DUTCH_HINTS):
        pts += 5
        why.append("dutch+5")

    return min(100, pts), " ".join(why)
