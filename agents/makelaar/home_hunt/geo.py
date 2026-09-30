"""Map a scraped area string to a preference tier. Lower number = more preferred.

The tiers below are an EXAMPLE ranking of Amsterdam neighbourhoods: replace them with
your own preferences (or your own city). The mechanics (longest-match, word
boundaries, postcode-district exclusion, optional commuter-city exception) are
generic."""
import os
import re

BULLSEYE = 0
GREAT = 1
FINE = 2
LOWER = 3
EXCLUDE = -1

_TIERS = {
    BULLSEYE: ("jordaan", "de pijp", "oud-west", "oud west", "oosterparkbuurt",
               "dapperbuurt", "vondelparkbuurt", "helmersbuurt", "da costabuurt",
               "kinkerbuurt"),
    GREAT: ("de baarsjes", "baarsjes", "westerpark", "vondelpark", "centrum", "oost",
            "museumkwartier", "rivierenbuurt", "frederik hendrikbuurt",
            "staatsliedenbuurt", "spaarndammerbuurt"),
    FINE: ("stadionbuurt", "apollobuurt", "beethovenstraat", "prinses irenebuurt",
           "hoofddorppleinbuurt", "schinkelbuurt", "willemspark", "amsterdam zuid",
           "oud-zuid", "oud zuid", "zuid", "buitenveldert", "houthavens", "erasmuspark",
           "nieuw sloten"),   # a Nieuw-West pocket kept by name (beats its 106x postcode)
    LOWER: ("bos en lommer", "bos-en-lommer", "boslommer",
            "landlust", "kolenkit", "kolenkitbuurt", "de kolenkit",
            "sloterdijk", "sloterdijk-centrum"),
    EXCLUDE: ("noord", "nieuw-west", "nieuw west", "slotervaart", "osdorp",
              "geuzenveld", "slotermeer",
              # far-west Nieuw-West buurt + main-street/square names (postcode/geocode
              # is the primary catch; these handle name-only listings). Full phrases
              # only - never bare "meer"/"vaart"/"slot"/"lelylaan" (collide with good
              # central streets like Amstelveenseweg / Overtoom / Sloterdijk).
              "overtoomse veld", "de aker", "tussen meer", "meer en vaart",
              "osdorpplein", "pieter calandlaan",   # accented names (Allebéplein etc.)
              # far NORTH-EAST corner - Indische Buurt + east harbour/islands + IJburg
              "indische buurt", "oostelijk havengebied", "oostelijke havengebied",
              "zeeburg", "zeeburgereiland", "ijburg", "knsm", "java-eiland",
              "javaeiland", "sporenburg", "borneo-eiland",
              "zuidoost", "bijlmer", "gein", "gaasperdam",   # are left to the geocode catch
              # Non-target CITIES/suburbs. Only Amsterdam (plus any opted-in commuter
              # city, see below) is wanted, so any other town is excluded. The right-boundary (see _present)
              # matches "hoofddorp" in "Hoofddorp60" but NOT in Amsterdam street names
              # like "Haarlemmerstraat"/"Amstelveenseweg" (a letter follows), and the
              # longer "hoofddorppleinbuurt" still wins as a kept area.
              # Amstelveen is another city → excluded.
              "amstelveen",
              "diemen", "hoofddorp", "haarlemmermeer", "hillegom", "weesp",
              "badhoevedorp", "haarlem", "almere", "zaandam", "zaanstad",
              "purmerend", "hilversum", "aalsmeer", "uithoorn", "ouderkerk",
              "abcoude", "lelystad", "hoorn", "alkmaar", "muiden", "naarden",
              "bussum", "schiphol", "nieuw-vennep", "leiderdorp", "oegstgeest",
              "voorhout", "katwijk", "noordwijk", "den haag", "rotterdam",
              "delft", "zoetermeer", "gouda", "rijswijk", "alphen",
              "utrecht", "leiden"),
}

_AREA_TO_TIER = {name: tier for tier, names in _TIERS.items() for name in names}

# Optional commuter-city exception, OFF by default: e.g. a nearby city with a direct
# train to your worksite. List cities in the env var HOME_HUNT_COMMUTER_CITIES (e.g.
# "haarlem") to keep listings within ~10 min walk of that city's main station
# (Centraal) while excluding the rest of the city. Coarse gate: "<city> centraal" plus
# any near-station names/postcodes you add below; the commute.py map-screenshot check
# is authoritative.
COMMUTER_CITIES_ENV = "HOME_HUNT_COMMUTER_CITIES"
# city -> near-station street names / postcodes. Ships empty. Format example:
#   _NEAR_CENTRAAL = {"haarlem": ("stationsplein", "2011")}
_NEAR_CENTRAAL = {}


def commuter_cities(env=None):
    """Lowercased cities with the commuter exception enabled (empty tuple = off)."""
    raw = (env if env is not None else os.environ).get(COMMUTER_CITIES_ENV, "")
    return tuple(c.strip().lower() for c in raw.split(",") if c.strip())


# Amsterdam PC4 district prefixes to EXCLUDE - catches postcode-only listings with no
# neighbourhood name: Noord (1020-1039, across the IJ), far-west Nieuw-West (1060-1069:
# Slotervaart/Osdorp/Geuzenveld/Slotermeer), Zuidoost/Bijlmer (1100-1109, below the ring).
_EXCLUDE_PC3 = ("102", "103", "106", "110")
# Specific far north-east PC4s (east harbour/islands + IJburg + Indische Buurt). PC4-precise
# because their PC3 prefixes collide with kept areas (101x = Centrum, 108x = Buitenveldert,
# 1093 = inner Oost) - only these exact zones are far enough + poorly connected to drop.
_EXCLUDE_PC4 = ("1019", "1086", "1087", "1088", "1095")
_AMS_PC4 = re.compile(r"\b(1[01]\d{2})(?!\d)")   # 10xx/11xx, tolerant of a mashed letter suffix


def _postcode_excluded(a):
    for m in _AMS_PC4.finditer(a):
        pc4 = m.group(1)
        if pc4[:3] in _EXCLUDE_PC3 or pc4 in _EXCLUDE_PC4:
            return True
    return False


def _present(token, a):
    """True if `token` appears in `a` as a COMPLETE token (a is already lowercased).
    Right boundary: a digit token must not be followed by a digit ('3511' ≠ '35110'),
    a name token must not be followed by a letter ('noord' ≠ 'noorderpark',
    'haarlem' ≠ 'haarlemmerstraat') - but a name MAY be followed by a digit, so a
    city mashed into a number like 'hoofddorp60' still matches."""
    tail = r"(?!\d)" if token.isdigit() else r"(?![a-z])"
    return re.search(r"\b" + re.escape(token) + tail, a) is not None


def _commuter_tier(a):
    """For an opted-in commuter city: FINE for a spot right by its Centraal, EXCLUDE for
    the rest of that city. None if no commuter city matches (or none is configured).
    Coarse postcode gate; exact walk-time is verified from the full address."""
    cities = commuter_cities()
    for city in cities:
        for token in (f"{city} centraal",) + _NEAR_CENTRAAL.get(city, ()):
            if _present(token, a):
                return FINE
    for city in cities:
        if _present(city, a):
            return EXCLUDE
    return None


def neighbourhood_tier(area):
    """Longest matching neighbourhood name wins (so 'oud-west' beats bare 'west').
    Matches on word boundaries so 'noord' does not match 'noorderpark'. Opted-in
    commuter cities get the near-Centraal exception (see commuter_cities)."""
    if not area:
        return None
    a = area.lower()
    commuter = _commuter_tier(a)
    if commuter is not None:
        return commuter
    best, best_len = None, -1
    for name, tier in _AREA_TO_TIER.items():
        if len(name) > best_len and _present(name, a):
            best, best_len = tier, len(name)
    # An explicitly recognised GOOD area name wins over a bad-looking postcode prefix -
    # e.g. "Nieuw Sloten" is Fine even though its 1066 postcode sits in the excluded 106x
    # Nieuw-West block. Postcode exclusion still catches postcode-only listings (no name).
    if best is not None and best != EXCLUDE:
        return best
    if _postcode_excluded(a):       # bad Amsterdam district by postcode (Noord/NW/Zuidoost)
        return EXCLUDE
    return best


def is_excluded(area):
    return neighbourhood_tier(area) == EXCLUDE
