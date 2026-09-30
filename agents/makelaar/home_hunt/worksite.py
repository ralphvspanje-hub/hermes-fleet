"""Work-commute refinement: drop / downrank listings that are too far to bike to
your worksite.

The worksite is configured with the env var HOME_HUNT_WORKSITE="lat,lon". When it is
unset (or unparseable) the commute filter is disabled: work_distance_km returns None
and refine_work_distance passes every decision through unchanged.

A listing's postcode is geocoded via the free Dutch PDOK locatieserver and the
straight-line distance to the worksite is computed. Everything is injectable (tests
pass a fake fetcher / distance_fn) so the core stays hermetic; live runs cache
postcode → lat/lon so each postcode is geocoded at most once. A geocode that lands
implausibly far (>25 km from the worksite, or from the city centre when no worksite is
set: a mis-match, e.g. a bare 4-digit postcode hitting another town) is discarded, so
a bad geocode never causes a false "too far" drop."""
import json
import math
import os
import re
import urllib.parse
import urllib.request
from .config import Config
from .models import Verdict
from . import geo

WORKSITE_ENV = "HOME_HUNT_WORKSITE"
_AMS_CENTRE = (52.3676, 4.9041)            # Dam square-ish; for an "is it in Amsterdam?" gate
_SANITY_KM = 25.0                          # a geocode beyond this is treated as a mis-match
_PC6 = re.compile(r"(\d{4})\s?([A-Za-z]{2})(?![A-Za-z])")  # 2 letters, not part of a word (city)
_PC4 = re.compile(r"\b(\d{4})\b")


def worksite_latlon(env=None):
    """The worksite as (lat, lon) from HOME_HUNT_WORKSITE="lat,lon", or None when unset
    or malformed (None disables the commute filter). Read on every call so tests and
    long-running processes see the current environment."""
    raw = (env if env is not None else os.environ).get(WORKSITE_ENV, "").strip()
    if not raw:
        return None
    try:
        lat, lon = (float(p) for p in raw.split(","))
    except ValueError:
        return None
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        return None
    return lat, lon


def _postcode(area):
    """Best postcode from an area string: full 6-char (preferred) else bare 4-digit."""
    if not area:
        return None
    m = _PC6.search(area)
    if m:
        return (m.group(1) + m.group(2)).upper()
    m = _PC4.search(area)
    return m.group(1) if m else None


def haversine(a, b):
    R = 6371.0
    dlat, dlon = math.radians(b[0] - a[0]), math.radians(b[1] - a[1])
    h = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(a[0])) * math.cos(math.radians(b[0])) * math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(h))


def _pdok_fetch(postcode):
    """Live geocode query to PDOK; returns the raw JSON text. Amsterdam-constrained."""
    q = urllib.parse.urlencode({
        "q": f"{postcode} Amsterdam", "rows": 1, "fl": "centroide_ll",
        "fq": "gemeentenaam:Amsterdam"})
    url = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?" + q
    with urllib.request.urlopen(url, timeout=15) as r:
        return r.read().decode("utf-8", "replace")


def _latlon_from_pdok(text):
    docs = (json.loads(text).get("response", {}) or {}).get("docs", [])
    if not docs or "centroide_ll" not in docs[0]:
        return None
    try:
        lon, lat = docs[0]["centroide_ll"].replace("POINT(", "").replace(")", "").split()
        return float(lat), float(lon)
    except Exception:
        return None


def geocode_latlon(area, fetcher=None, cache=None):
    """The listing's postcode geocoded to (lat, lon), or None (no postcode / bad geocode).
    A geocode landing >_SANITY_KM from the worksite (or the city centre if no worksite
    is set) is discarded as a mis-match. Cached per postcode and shared by the
    work-distance and transit checks, so a postcode is geocoded at most once.
    `fetcher(postcode)->json_text` and `cache` are injectable."""
    pc = _postcode(area)
    if not pc:
        return None
    cache = cache if cache is not None else _CACHE
    if pc in cache:
        return cache[pc]
    try:
        latlon = _latlon_from_pdok((fetcher or _pdok_fetch)(pc))
    except Exception:
        latlon = None
    anchor = worksite_latlon() or _AMS_CENTRE
    if latlon is not None and haversine(anchor, latlon) > _SANITY_KM:
        latlon = None                      # implausible → treat as un-geocodable
    cache[pc] = latlon
    return latlon


def work_distance_km(area, fetcher=None, cache=None):
    """Straight-line km from the listing's postcode to the worksite, or None if the
    worksite is unset, the postcode is unknown, or the geocode is bad."""
    site = worksite_latlon()
    if site is None:
        return None
    latlon = geocode_latlon(area, fetcher=fetcher, cache=cache)
    return haversine(site, latlon) if latlon else None


_CACHE = {}   # process-level postcode → lat/lon (or None) cache for live runs


def refine_work_distance(decisions, distance_fn=None, transit_fn=None, config=None):
    """Score/drop SHOW/FLAG listings by commute to the worksite. A listing too far to
    bike is DROPPED, UNLESS it's a short walk from a station with a fast direct ride
    to work (see transit.py); then it's KEPT and tagged. Closer-to-work +
    transit-connected listings rank higher.
    `distance_fn(area)->km|None` and `transit_fn(area)->(station,ride_min,walk_m)|None`
    are injectable (defaults = live PDOK geocode). With no distance_fn and no
    HOME_HUNT_WORKSITE set, the filter is disabled and decisions pass through.
    Excluded areas are already dropped upstream, so transit only ever rescues listings
    in wanted neighbourhoods."""
    config = config or Config()
    if distance_fn is None and worksite_latlon() is None:
        return list(decisions)             # no worksite configured → commute filter off
    distance_fn = distance_fn or work_distance_km
    out = []
    for d in decisions:
        # Opted-in commuter cities are allowed via the near-Centraal exception (geo.py),
        # not by distance to the worksite, so the distance rule must not drop them.
        area_l = (d.listing.area or "").lower()
        if any(geo._present(c, area_l) for c in geo.commuter_cities()):
            out.append(d)
            continue
        if d.verdict in (Verdict.SHOW, Verdict.FLAG):
            km = distance_fn(d.listing.area)
            transit = transit_fn(d.listing.area) if transit_fn else None
            if km is not None and km > config.max_commute_km:
                if transit is not None:        # bike-far but a quick transit ride to work → keep
                    name, ride, walk = transit
                    out.append(type(d)(
                        listing=d.listing, verdict=d.verdict, score=min(100, d.score + 8),
                        reasons=d.reasons + [f"transit: ~{ride}min to work via {name} ({int(walk)}m walk)"],
                        scam_flags=d.scam_flags))
                    continue
                out.append(type(d)(
                    listing=d.listing, verdict=Verdict.DROP, score=0,
                    reasons=[f"commute: {km:.1f}km to work (> {config.max_commute_km}km), no quick transit to work"]
                            + list(d.reasons),
                    scam_flags=d.scam_flags))
                continue
            if km is not None:
                bonus = max(0, int(12 * (1 - km / config.max_commute_km)))
                reasons = d.reasons + [f"commute {km:.1f}km+{bonus}"]
                if transit is not None:
                    name, ride, walk = transit
                    bonus += 4
                    reasons = reasons + [f"+transit ~{ride}min to work"]
                out.append(type(d)(
                    listing=d.listing, verdict=d.verdict, score=min(100, d.score + bonus),
                    reasons=reasons, scam_flags=d.scam_flags))
                continue
        out.append(d)
    return out


# --- street-name → district geocode -----------------------------------------
# Some sources send listings with area=None and only a street name in the title
# (e.g. "August Allebeplein"). With no postcode the postcode-district exclusion in
# geo.py can't fire, so a street in an excluded district slips through as SHOW. We
# geocode the street via PDOK to recover its postcode and reuse the same district
# exclusion. PDOK returns the postcode (in `weergavenaam`) and a centroid even for a
# bare street query.

_CITY_KM = 16.0                            # a geocode beyond this isn't trusted as Amsterdam
_PC6_IN_TEXT = re.compile(r"\b(1\d{3})\s?([A-Za-z]{2})\b")   # full postcode in a PDOK name
_PC4_IN_TEXT = re.compile(r"\b(1\d{3})\b")                   # 4-digit fallback
_GEO_CACHE = {}                            # process-level street → postcode (or None) cache


def _pdok_street_fetch(text):
    """Live PDOK free-text query for a street/area; returns raw JSON text, Amsterdam-only."""
    q = urllib.parse.urlencode({
        "q": f"{text} Amsterdam", "rows": 5, "fl": "type,weergavenaam,centroide_ll",
        "fq": "gemeentenaam:Amsterdam"})
    url = "https://api.pdok.nl/bzk/locatieserver/search/v3_1/free?" + q
    with urllib.request.urlopen(url, timeout=15) as r:
        return r.read().decode("utf-8", "replace")


def _doc_latlon(doc):
    cl = doc.get("centroide_ll")
    if not cl:
        return None
    try:
        lon, lat = cl.replace("POINT(", "").replace(")", "").split()
        return float(lat), float(lon)
    except Exception:
        return None


def geocode_postcode(text, fetcher=None, cache=None):
    """Geocode a free-text street/area and return its Amsterdam postcode (PC6 if present,
    else PC4), or None. Only a match whose centroid lands inside Amsterdam (within
    _CITY_KM of the centre) is trusted, so a fuzzy match to another town never produces a
    false exclusion. `fetcher(text)->json_text` and `cache` are injectable."""
    if not text:
        return None
    key = text.strip().lower()
    cache = cache if cache is not None else _GEO_CACHE
    if key in cache:
        return cache[key]
    try:
        docs = (json.loads((fetcher or _pdok_street_fetch)(text)).get("response", {}) or {}).get("docs", [])
    except Exception:
        docs = []
    result = None
    for doc in docs:
        latlon = _doc_latlon(doc)
        if latlon is not None and haversine(_AMS_CENTRE, latlon) > _CITY_KM:
            continue                       # fuzzy match outside Amsterdam → ignore
        name = doc.get("weergavenaam", "") or ""
        m = _PC6_IN_TEXT.search(name)
        if m:
            result = (m.group(1) + m.group(2)).upper()
            break
        m = _PC4_IN_TEXT.search(name)
        if m:
            result = m.group(1)
            break
    cache[key] = result
    return result


def refine_geo_geocode(decisions, postcode_fn=None, config=None):
    """Catch postcode-less listings whose only location hint is a street name and that
    fall in an excluded Amsterdam district (Noord / far-west Nieuw-West / Zuidoost). For
    each SHOW/FLAG with no postcode and no recognised neighbourhood, geocode the street to
    a postcode and DROP it if that postcode's district is excluded. A failed/ambiguous
    geocode never drops. `postcode_fn(text)->postcode|None` is injectable."""
    postcode_fn = postcode_fn or geocode_postcode
    out = []
    for d in decisions:
        if d.verdict in (Verdict.SHOW, Verdict.FLAG):
            listing = d.listing
            text = " ".join(p for p in (listing.area, listing.title) if p)
            if _postcode(text) is None and geo.neighbourhood_tier(text) is None:
                pc = postcode_fn(text)
                if pc and geo.is_excluded(pc):
                    out.append(type(d)(
                        listing=listing, verdict=Verdict.DROP, score=0,
                        reasons=[f"outside target area (geocoded {pc} = excluded district)"] + list(d.reasons),
                        scam_flags=d.scam_flags))
                    continue
        out.append(d)
    return out
