import pytest
from home_hunt import geo

# Example near-station data for the commuter-city tests (geo._NEAR_CENTRAAL ships empty).
EXAMPLE_NEAR = {"haarlem": ("stationsplein", "2011")}


@pytest.fixture
def commuter_example(monkeypatch):
    """Opt in to the commuter-city exception for an example city."""
    monkeypatch.setattr(geo, "_NEAR_CENTRAAL", EXAMPLE_NEAR)
    monkeypatch.setenv(geo.COMMUTER_CITIES_ENV, "haarlem")
