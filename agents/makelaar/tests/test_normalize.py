from home_hunt.normalize import parse_price, infer_housing_type, parse_available_from
from home_hunt.models import HousingType


def test_parse_price():
    assert parse_price("€ 1.250 p/m") == 1250
    assert parse_price("€950") == 950
    assert parse_price("1.495 per maand") == 1495
    assert parse_price("Prijs op aanvraag") is None
    assert parse_price("") is None
    assert parse_price(None) is None


def test_parse_price_sanity_floor():
    # a parsed rent under €300 is almost certainly a mis-parse (service costs / stray
    # number), not a real Amsterdam rent → treat as unknown.
    assert parse_price("€ 95") is None
    assert parse_price("€ 250") is None
    assert parse_price("€ 1.150") == 1150
    assert parse_price("€ 300") == 300        # the floor itself is allowed


def test_infer_housing_type():
    assert infer_housing_type("Studio te huur") == HousingType.SOLO
    assert infer_housing_type("3-kamer appartement") == HousingType.SOLO   # room-COUNT, not a room
    assert infer_housing_type("Ruime kamer in Amsterdam") == HousingType.SHARED
    assert infer_housing_type("Room for rent, nice flatmates") == HousingType.SHARED
    assert infer_housing_type("Te huur in Zuid") == HousingType.UNKNOWN


def test_parse_available_from():
    assert parse_available_from("Per direct") == "asap"
    assert parse_available_from("Available immediately") == "asap"
    assert parse_available_from("01-08-2026") == "01-08-2026"
    assert parse_available_from("") is None
