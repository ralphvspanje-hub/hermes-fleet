from typing import Optional
from .models import Listing, HousingType
from . import phrases, geo

# Opt-in household exclusions: Config.exclude_household_tags picks which ones apply.
# tag -> (detector, drop reason)
HOUSEHOLD_TAGS = {
    "women_only": (phrases.has_women_only, "women-only"),
    "student_only": (phrases.has_student_only, "student-only house"),
}


def hard_drop_reason(listing: Listing, config) -> Optional[str]:
    """Return the first certain-dealbreaker reason, or None to keep."""
    text = f"{listing.title}\n{listing.description}"

    if listing.registration is False or phrases.has_no_registration(text):
        return "no registration"
    if listing.is_sublet or phrases.has_sublet(text):
        return "sublet/onderhuur"
    if listing.is_woningruil or phrases.has_woningruil(text):
        return "woningruil (home-swap)"
    if phrases.has_temporary(text) or phrases.has_short_term(text):
        return "temporary/antikraak/short-stay"
    for tag in getattr(config, "exclude_household_tags", ()) or ():
        check = HOUSEHOLD_TAGS.get(tag)
        if check is not None and check[0](text):
            return check[1]

    if listing.housing_type == HousingType.SHARED and not getattr(config, "allow_shared", False):
        return "shared housing (filtered out)"

    if listing.price_eur is not None:
        if listing.housing_type == HousingType.SHARED and listing.price_eur > config.shared_max_eur:
            return f"shared over €{config.shared_max_eur}"
        if listing.housing_type != HousingType.SHARED and listing.price_eur > config.solo_max_eur:
            return f"solo over €{config.solo_max_eur}"

    # check the title too: email/portal listings often put the city in the title
    # (e.g. "Voorbeeldlaan, Hoofddorp60 m²") with no structured area field.
    location = " ".join(p for p in (listing.area, listing.title) if p)
    if geo.is_excluded(location):
        return "outside target area"

    # income_eur == 0 means "income unknown/not set": the max-income filter is off.
    if not config.income_eur:
        return None
    max_inc = listing.max_income_eur if listing.max_income_eur is not None else phrases.extract_max_income(text)
    if max_inc is not None and max_inc < config.income_eur:
        return f"max income €{max_inc} < €{config.income_eur}"

    return None
