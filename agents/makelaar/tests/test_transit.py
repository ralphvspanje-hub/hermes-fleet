import json
import pytest
from home_hunt import transit
from home_hunt.transit import nearest_direct_station, transit_for_area

STATIONS = (
    ("De Pijp (M52)",    52.35221, 4.89133, 8),
    ("Postjesweg (M50)", 52.36426, 4.84725, 12),
)


@pytest.fixture(autouse=True)
def _stations(monkeypatch):
    monkeypatch.setattr(transit, "DIRECT_STATIONS", STATIONS)


def test_ships_empty_by_default(monkeypatch):
    monkeypatch.undo()
    assert transit.DIRECT_STATIONS == ()
    assert nearest_direct_station((52.35221, 4.89133)) is None


def test_nearest_station_within_walk():
    # a point ~150 m from Postjesweg metro → connected, returns that station + ride time
    near_postjesweg = (52.36500, 4.84725)
    hit = nearest_direct_station(near_postjesweg)
    assert hit is not None
    name, ride, walk = hit
    assert "Postjesweg" in name
    assert ride == 12
    assert walk < 200


def test_no_station_when_far():
    # middle of the Nieuwe Meer / nowhere near a curated station
    assert nearest_direct_station((52.32000, 4.80000)) is None


def test_none_latlon_is_none():
    assert nearest_direct_station(None) is None


def test_transit_for_area_geocodes_then_matches():
    # PDOK-shaped geocode of a postcode that lands next to De Pijp (M52) station
    def fake_fetch(pc):
        return json.dumps({"response": {"docs": [
            {"centroide_ll": "POINT(4.89133 52.35221)"}]}})
    hit = transit_for_area("1073XX Amsterdam", fetcher=fake_fetch, cache={})
    assert hit is not None and "De Pijp" in hit[0]


def test_transit_for_area_none_without_postcode():
    assert transit_for_area("De Pijp", fetcher=lambda pc: "{}", cache={}) is None
