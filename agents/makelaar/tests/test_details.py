from home_hunt.details import refine_with_details
from home_hunt.models import Listing, HousingType, Verdict
from home_hunt.config import Config
from home_hunt.classify import classify


def _show(sid, url="https://x/obj/1"):
    return classify(Listing(source="x", source_id=sid, url=url, title="Studio", description="",
                            price_eur=1200, housing_type=HousingType.SOLO, area="De Pijp",
                            registration=True), Config())


def test_detail_drops_short_term_lease():
    d = _show("a")
    out = refine_with_details([d], fetcher=lambda url: "Huurperiode: beschikbaar voor 2 maanden.")
    assert out[0].verdict == Verdict.DROP
    assert "detail" in out[0].reasons[0].lower()


def test_detail_keeps_long_lease():
    d = _show("b")
    out = refine_with_details([d], fetcher=lambda url: "Voor ten minste 12 maanden, daarna onbepaalde tijd.")
    assert out[0].verdict == d.verdict          # 12-month minimum is fine


def test_detail_drops_income_cap_and_no_registration():
    a = _show("c")
    out = refine_with_details([a], fetcher=lambda url: "Maximaal inkomen €40.000 per jaar vereist.",
                              config=Config(income_eur=50000))
    assert out[0].verdict == Verdict.DROP
    b = _show("d")
    out2 = refine_with_details([b], fetcher=lambda url: "Let op: inschrijving niet mogelijk op dit adres.")
    assert out2[0].verdict == Verdict.DROP


def test_detail_fetch_error_keeps_listing():
    d = _show("e")

    def boom(url):
        raise RuntimeError("network down")

    out = refine_with_details([d], fetcher=boom)
    assert out[0].verdict == d.verdict          # a failed fetch never drops


def test_detail_only_fetches_shown():
    dropped = classify(Listing(source="x", source_id="f", url="u", title="Studio", description="",
                               price_eur=1200, housing_type=HousingType.SOLO, area="Bijlmer",
                               registration=True), Config())   # area-excluded → DROP
    calls = []
    refine_with_details([dropped], fetcher=lambda url: calls.append(url) or "")
    assert calls == []                          # don't waste fetches on already-dropped listings
