import json
import pytest
from home_hunt.worksite import (refine_work_distance, _postcode, haversine,
                                 work_distance_km, worksite_latlon, WORKSITE_ENV,
                                 geocode_postcode, refine_geo_geocode)
from home_hunt.models import Listing, HousingType, Verdict
from home_hunt.config import Config
from home_hunt.classify import classify

# Amsterdam Centraal station: a public landmark used as the test worksite.
CENTRAAL = (52.3791, 4.9003)


@pytest.fixture
def worksite(monkeypatch):
    monkeypatch.setenv(WORKSITE_ENV, "52.3791,4.9003")
    return CENTRAAL


@pytest.fixture
def no_worksite(monkeypatch):
    monkeypatch.delenv(WORKSITE_ENV, raising=False)


def _show(sid, area):
    return classify(Listing(source="x", source_id=sid, url="u", title="Studio", description="",
                            price_eur=1200, housing_type=HousingType.SOLO, area=area,
                            registration=True), Config())


def test_postcode_extraction():
    assert _postcode("1019SE Amsterdam") == "1019SE"
    assert _postcode("1019 SE Amsterdam") == "1019SE"
    assert _postcode("1072 Amsterdam") == "1072"
    assert _postcode("De Pijp") is None


def test_haversine_is_small_for_near_points():
    assert 0 < haversine(CENTRAAL, (52.37, 4.89)) < 5
    assert haversine(CENTRAAL, CENTRAAL) == 0


def test_worksite_read_from_env(worksite):
    assert worksite_latlon() == CENTRAAL


def test_worksite_malformed_env_is_none(monkeypatch):
    for bad in ("", "52.37", "abc,def", "999,4.9"):
        monkeypatch.setenv(WORKSITE_ENV, bad)
        assert worksite_latlon() is None, bad


def test_unset_worksite_disables_commute_filter(no_worksite):
    # no HOME_HUNT_WORKSITE → no distance, and the refine passes everything through
    assert worksite_latlon() is None
    calls = []
    fetch = lambda pc: calls.append(pc) or "{}"
    assert work_distance_km("1011AB Amsterdam", fetcher=fetch, cache={}) is None
    assert calls == []                                  # never even geocodes
    d = _show("x", "1011AB Amsterdam")
    out = refine_work_distance([d])                     # default distance_fn, no worksite
    assert out[0].verdict == d.verdict and out[0].score == d.score
    assert not any("commute" in r for r in out[0].reasons)


def test_refine_drops_too_far_keeps_near():
    far = _show("far", "1011AB Amsterdam")     # Centrum (kept), made bike-far via the stub
    near = _show("near", "1012AB Amsterdam")
    out = refine_work_distance([far, near],
                               distance_fn=lambda a: 9.2 if "1011" in a else 1.0)
    by = {d.listing.source_id: d for d in out}
    assert by["far"].verdict == Verdict.DROP
    assert "commute" in " ".join(by["far"].reasons).lower()
    assert by["near"].verdict == near.verdict        # near kept


def test_refine_exempts_commuter_city(commuter_example):
    # an opted-in commuter city is allowed via the near-Centraal exception, not distance
    u = _show("ut", "2011 AB Haarlem")
    assert u.verdict in (Verdict.SHOW, Verdict.FLAG)
    out = refine_work_distance([u], distance_fn=lambda a: 35.0)   # ~35km from the worksite
    assert out[0].verdict == u.verdict                            # NOT dropped


def test_refine_unknown_distance_never_drops():
    d = _show("u", "De Pijp")                          # no postcode → distance unknown
    out = refine_work_distance([d], distance_fn=lambda a: None)
    assert out[0].verdict == d.verdict


def test_work_distance_km_parses_pdok_and_sanity_bounds(worksite):
    def fake_fetch(pc):
        # PDOK-shaped: POINT(lon lat). A near point for 1012, a bogus far one otherwise.
        if pc.startswith("1012"):
            return json.dumps({"response": {"docs": [{"centroide_ll": "POINT(4.8960 52.3760)"}]}})
        return json.dumps({"response": {"docs": [{"centroide_ll": "POINT(5.10 52.09)"}]}})  # ~35 km away
    near = work_distance_km("1012AB Amsterdam", fetcher=fake_fetch, cache={})
    assert near is not None and near < 1.0
    # a >25km geocode is treated as a bad result → None (never a false "too far")
    assert work_distance_km("9999ZZ Amsterdam", fetcher=fake_fetch, cache={}) is None


# --- transit-to-work rescue / boost ---

def test_refine_transit_rescues_bikefar_listing():
    far = _show("far", "De Pijp")            # SHOW, then injected distance makes it bike-far
    out = refine_work_distance([far], distance_fn=lambda a: 9.0,
                               transit_fn=lambda a: ("Sloterdijk (M50+rail)", 14, 500.0))
    assert out[0].verdict == far.verdict      # NOT dropped: quick transit to work
    assert "transit" in " ".join(out[0].reasons).lower()


def test_refine_drops_bikefar_without_transit():
    far = _show("far", "De Pijp")
    out = refine_work_distance([far], distance_fn=lambda a: 9.0, transit_fn=lambda a: None)
    assert out[0].verdict == Verdict.DROP
    assert "no quick transit" in " ".join(out[0].reasons).lower()


def test_refine_transit_bonus_for_near_listing():
    near = _show("n", "De Pijp")
    base = refine_work_distance([near], distance_fn=lambda a: 3.0, transit_fn=lambda a: None)
    boosted = refine_work_distance([near], distance_fn=lambda a: 3.0,
                                   transit_fn=lambda a: ("De Pijp (M52)", 8, 300.0))
    assert boosted[0].score > base[0].score   # transit-connected ranks higher
    assert "transit" in " ".join(boosted[0].reasons).lower()


# --- street-name → district geocode (catches postcode-less far-west leaks) ---

def _pdok_street(pc_full, lon, lat):
    """PDOK free-search shape: a 'weg' doc then a 'postcode' doc carrying the postcode."""
    return json.dumps({"response": {"docs": [
        {"type": "weg", "weergavenaam": "Some Street, Amsterdam",
         "centroide_ll": "POINT(%s %s)" % (lon, lat)},
        {"type": "postcode", "weergavenaam": "Some Street, %s Amsterdam" % pc_full,
         "centroide_ll": "POINT(%s %s)" % (lon, lat)},
    ]}})


def test_geocode_postcode_extracts_amsterdam_postcode():
    pc = geocode_postcode("August Allebeplein",
                          fetcher=lambda q: _pdok_street("1062AA", 4.838, 52.363), cache={})
    assert pc is not None and pc.startswith("1062")


def test_geocode_postcode_none_when_no_match():
    empty = json.dumps({"response": {"docs": []}})
    assert geocode_postcode("Nowhere", fetcher=lambda q: empty, cache={}) is None


def test_geocode_postcode_rejects_far_centroid():
    # a fuzzy match landing far outside Amsterdam must not be trusted (even with a 1xxx PC)
    far = _pdok_street("1011AB", 6.50, 53.20)   # ~Groningen-ish coords
    assert geocode_postcode("Some Street", fetcher=lambda q: far, cache={}) is None


def test_refine_geocode_drops_excluded_district_street_only():
    # area=None, only a Nieuw-West street name in the title → geocode → 1062 → DROP
    far = _show("far", None)
    far = type(far)(listing=Listing(source="x", source_id="far", url="u",
                                    title="Studio August Allebeplein", description="",
                                    price_eur=1200, housing_type=HousingType.SOLO,
                                    area=None, registration=True),
                    verdict=far.verdict, score=far.score, reasons=far.reasons,
                    scam_flags=far.scam_flags)
    assert far.verdict in (Verdict.SHOW, Verdict.FLAG)
    out = refine_geo_geocode([far], postcode_fn=lambda t: "1062AA")
    assert out[0].verdict == Verdict.DROP
    assert "area" in " ".join(out[0].reasons).lower()


def test_refine_geocode_keeps_good_district_street_only():
    good = _show("g", None)
    good = type(good)(listing=Listing(source="x", source_id="g", url="u",
                                      title="Studio Van Ostadestraat", description="",
                                      price_eur=1200, housing_type=HousingType.SOLO,
                                      area=None, registration=True),
                      verdict=good.verdict, score=good.score, reasons=good.reasons,
                      scam_flags=good.scam_flags)
    out = refine_geo_geocode([good], postcode_fn=lambda t: "1072SL")
    assert out[0].verdict == good.verdict      # De Pijp postcode → kept


def test_refine_geocode_skips_when_postcode_present():
    calls = []
    d = _show("p", "1072SL Amsterdam")
    out = refine_geo_geocode([d], postcode_fn=lambda t: calls.append(t) or "1062AA")
    assert calls == []                         # already has a postcode → not geocoded
    assert out[0].verdict == d.verdict


def test_refine_geocode_unknown_never_drops():
    d = _show("u", None)
    out = refine_geo_geocode([d], postcode_fn=lambda t: None)
    assert out[0].verdict == d.verdict
