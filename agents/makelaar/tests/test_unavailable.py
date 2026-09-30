from home_hunt import phrases
from home_hunt.details import detail_dropper
from home_hunt.config import Config


def test_reserved_or_rented_status_detected():
    assert phrases.has_unavailable("Agency - Gereserveerd: Voorbeeldstraat 12, amsterdam")
    assert phrases.has_unavailable("Agency - Verhuurd: Fictieweg 8")
    assert phrases.has_unavailable("Deze woning is verhuurd")
    assert phrases.has_unavailable("Woning onder optie")


def test_boilerplate_and_footers_not_flagged():
    # agency boilerplate "...heeft ruim woningen verhuurd" must NOT trip it
    assert not phrases.has_unavailable(
        "Agency is een professionele verhuurder en heeft ruim woningen verhuurd in beheer")
    assert not phrases.has_unavailable("Agency - Te huur: Proefgracht 5, amsterdam")
    assert not phrases.has_unavailable("All rights reserved")          # English footer
    assert not phrases.has_unavailable("Inschrijven mogelijk, per direct beschikbaar")


def test_detail_dropper_drops_reserved_keeps_live():
    assert detail_dropper("Agency - Gereserveerd: Voorbeeldstraat 12", Config()) is not None
    assert detail_dropper("Agency - Te huur: Proefgracht 5", Config()) is None
