from home_hunt.details import refine_with_details
from home_hunt.models import Listing, HousingType, Verdict
from home_hunt.config import Config
from home_hunt.classify import classify


def _show(url):
    return classify(Listing(source="example", source_id=url, url=url, title="Studio",
                            description="", price_eur=1200, housing_type=HousingType.SOLO,
                            area="De Pijp", registration=True), Config())


def test_unfetchable_listing_is_flagged_not_dropped():
    # the site blocks us (e.g. a 403) → keep but flag, never silently trust
    def boom(url):
        raise RuntimeError("403 Forbidden")
    out = refine_with_details([_show("u")], fetcher=boom)
    assert out[0].verdict in (Verdict.SHOW, Verdict.FLAG)          # not dropped
    assert any("unverified" in r.lower() for r in out[0].reasons)  # but flagged


def test_readable_live_listing_not_flagged():
    out = refine_with_details([_show("u")],
                              fetcher=lambda url: "Te huur, per direct, inschrijving mogelijk")
    assert out[0].verdict in (Verdict.SHOW, Verdict.FLAG)
    assert not any("unverified" in r.lower() for r in out[0].reasons)
