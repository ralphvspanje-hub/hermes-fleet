"""Public-transport-to-work rescue/boost.

A listing too far to bike to the worksite can still be a fine commute if it's a short
walk from a station with a fast, ~direct ride to work. We keep a small curated list of
such stations and check the listing's geocoded location against them.

DIRECT_STATIONS ships empty: fill it with stations that have a direct line to your
own worksite (see the commented format example below).

Two deliberate choices:
  * Stations in EXCLUDED areas (geo.py) are omitted: a great commute must never rescue
    a listing in an area you've ruled out. Excluded areas are also already dropped
    upstream, so their stations would be useless here anyway.
  * Coordinates are PDOK-verified street/station points (lat, lon).

This is purely additive: it only ever KEEPS a bike-far listing that would otherwise be
dropped, or nudges a kept listing's rank up. It never drops anything new.
"""
from .worksite import haversine, geocode_latlon

# Stations with a direct line to YOUR worksite, as (name, lat, lon, approx
# ride-minutes to work). Empty by default = no transit rescue/boost.
# FORMAT EXAMPLE ONLY (a hypothetical worksite at Amsterdam Centraal; the station
# names and minutes are illustrative, not a real timetable):
#
# DIRECT_STATIONS = (
#     ("Example Metro Stop A", 52.3600, 4.9000, 6),
#     ("Example Rail Stop B",  52.3900, 4.8500, 10),
# )
DIRECT_STATIONS = ()
WALK_M = 900.0          # within ~10-11 min walk of a direct station = transit-connected
MAX_RIDE_MIN = 30       # public transport to work up to ~30 min counts as a fine commute


def nearest_direct_station(latlon):
    """Return (name, ride_min, walk_m) for the closest direct-to-work station within
    WALK_M of `latlon`, or None if none is close enough / latlon is unknown."""
    if latlon is None:
        return None
    best = None
    for name, lat, lon, ride in DIRECT_STATIONS:
        if ride > MAX_RIDE_MIN:
            continue
        walk_m = haversine(latlon, (lat, lon)) * 1000.0
        if walk_m <= WALK_M and (best is None or walk_m < best[2]):
            best = (name, ride, walk_m)
    return best


def transit_for_area(area, fetcher=None, cache=None):
    """Live: geocode the listing's postcode and return its nearest direct-to-work station
    (name, ride_min, walk_m), or None. Injectable via geocode_latlon's fetcher/cache."""
    return nearest_direct_station(geocode_latlon(area, fetcher=fetcher, cache=cache))
