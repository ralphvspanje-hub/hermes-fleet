from home_hunt.models import Listing, HousingType
from home_hunt.scam import assess


def _l(desc):
    return Listing(source="t", source_id="1", url="u", title="", description=desc,
                   price_eur=900, housing_type=HousingType.SOLO, area="De Pijp")


def test_reject_tier_money_before_viewing():
    tier, flags = assess(_l("Please pay the deposit to secure the room via Western Union"))
    assert tier == "reject"
    assert flags


def test_flag_tier_offplatform_and_pressure():
    tier, flags = assess(_l("Message me on WhatsApp, high demand, decide today"))
    assert tier == "flag"


def test_none_tier_clean():
    tier, flags = assess(_l("Bright studio, viewing on Saturday, contract on name"))
    assert tier == "none"
    assert flags == []
