import pytest
from home_hunt import geo


@pytest.fixture
def commuters(commuter_example):
    return commuter_example


@pytest.fixture(autouse=True)
def _no_commuters_by_default(monkeypatch):
    monkeypatch.delenv(geo.COMMUTER_CITIES_ENV, raising=False)


def test_tiers():
    assert geo.neighbourhood_tier("Jordaan") == geo.BULLSEYE
    assert geo.neighbourhood_tier("De Pijp") == geo.BULLSEYE
    assert geo.neighbourhood_tier("De Baarsjes") == geo.GREAT
    assert geo.neighbourhood_tier("Amsterdam Oost") == geo.GREAT
    assert geo.neighbourhood_tier("Stadionbuurt") == geo.FINE
    assert geo.neighbourhood_tier("Buitenveldert") == geo.FINE
    assert geo.neighbourhood_tier("Bos en Lommer") == geo.LOWER
    assert geo.neighbourhood_tier("Bijlmer") == geo.EXCLUDE
    assert geo.neighbourhood_tier("metro Gein") == geo.EXCLUDE
    assert geo.neighbourhood_tier("Mystery Town") is None


def test_is_excluded():
    assert geo.is_excluded("Amsterdam Noord")
    assert not geo.is_excluded("De Pijp")
    assert not geo.is_excluded(None)


def test_word_boundary_no_false_exclude():
    # "noord" must not match inside "Noorderpark"
    assert geo.neighbourhood_tier("Noorderpark") is None
    assert not geo.is_excluded("Noorderpark")
    assert geo.neighbourhood_tier("Amsterdam Noord") == geo.EXCLUDE  # real Noord still excluded


def test_zuid_gazetteer():
    assert geo.neighbourhood_tier("Amsterdam Zuid") == geo.FINE
    assert geo.neighbourhood_tier("Zuid") == geo.FINE
    assert geo.neighbourhood_tier("Zuidoost") == geo.EXCLUDE   # still excluded, not promoted by 'zuid'
    assert geo.neighbourhood_tier("Oud-Zuid") == geo.FINE      # longer match still wins
    assert geo.neighbourhood_tier("Oosterparkbuurt") == geo.BULLSEYE   # beats bare "oost"


def test_amstelveen_excluded_buitenveldert_kept():
    assert geo.neighbourhood_tier("Amstelveen") == geo.EXCLUDE      # another city, out
    assert geo.neighbourhood_tier("Amstelveen-Noord") == geo.EXCLUDE
    assert geo.neighbourhood_tier("Buitenveldert") == geo.FINE      # Amsterdam district, kept


def test_commuter_exception_off_by_default():
    assert geo.commuter_cities() == ()
    # without opt-in, other cities are simply excluded, near-Centraal or not
    assert geo.neighbourhood_tier("Haarlem Centraal") == geo.EXCLUDE
    assert geo.neighbourhood_tier("2011 AB Haarlem") == geo.EXCLUDE
    assert geo._NEAR_CENTRAAL == {}                      # ships without city data


def test_commuter_cities_parsing():
    assert geo.commuter_cities({"HOME_HUNT_COMMUTER_CITIES": " Haarlem, ,delft "}) == ("haarlem", "delft")


def test_commuter_exception_when_opted_in(commuters):
    assert geo.neighbourhood_tier("Haarlem Centraal") == geo.FINE
    assert geo.neighbourhood_tier("2011 AB Haarlem") == geo.FINE     # near-CS postcode beats city-exclude
    assert geo.neighbourhood_tier("Stationsplein, Haarlem") == geo.FINE
    assert geo.neighbourhood_tier("Haarlem Schalkwijk") == geo.EXCLUDE
    assert not geo.is_excluded("Haarlemmerstraat")   # Amsterdam street, not the city


def test_far_suburbs_excluded():
    # a regional "amsterdam" search can leak far suburbs → exclude them
    assert geo.is_excluded("1113 Diemen")
    assert geo.neighbourhood_tier("Hillegom") == geo.EXCLUDE
    assert geo.neighbourhood_tier("Hoofddorp") == geo.EXCLUDE
    assert geo.is_excluded("Weesp")
    assert geo.is_excluded("Badhoevedorp")
    # but the Amsterdam neighbourhood Hoofddorppleinbuurt must NOT be caught by "hoofddorp"
    assert geo.neighbourhood_tier("Hoofddorppleinbuurt") == geo.FINE


def test_city_mashed_with_number_in_title_excluded(commuters):
    # "...Hoofddorp60 m2..." (city stuck to a number), area None
    assert geo.neighbourhood_tier("Voorbeeldlaan, Hoofddorp60 m2") == geo.EXCLUDE
    assert geo.is_excluded("Hoofddorp60 m2 Furnished Apartment")
    assert geo.neighbourhood_tier("2011AB Haarlem") == geo.FINE     # postcode mashed with letters


def test_amsterdam_bad_districts_by_postcode_only():
    # postcode-only listings (no neighbourhood name) must still be excluded by district
    assert geo.neighbourhood_tier("1031 Amsterdam") == geo.EXCLUDE      # Noord
    assert geo.neighbourhood_tier("1033SC Amsterdam") == geo.EXCLUDE    # Noord, mashed postcode
    assert geo.neighbourhood_tier("1025 Amsterdam") == geo.EXCLUDE      # Noord
    assert geo.neighbourhood_tier("1064 Amsterdam") == geo.EXCLUDE      # Nieuw-West (far west)
    assert geo.neighbourhood_tier("1103 Amsterdam") == geo.EXCLUDE      # Zuidoost/Bijlmer
    # good districts by postcode are NOT excluded
    assert geo.neighbourhood_tier("1096DT Amsterdam") != geo.EXCLUDE    # Overamstel
    assert geo.neighbourhood_tier("1059 Amsterdam") != geo.EXCLUDE      # Hoofddorppleinbuurt (Zuid)


def test_northeast_corner_excluded():
    # Indische Buurt + east harbour/islands + IJburg = too far NE (poor bike + transit)
    assert geo.is_excluded("Indische Buurt")
    assert geo.is_excluded("IJburg")
    assert geo.is_excluded("Oostelijk Havengebied")
    assert geo.is_excluded("Java-eiland")
    assert geo.is_excluded("1095PG Amsterdam")     # Indische Buurt by postcode
    assert geo.is_excluded("1019 Amsterdam")       # east harbour (KNSM/Java)
    assert geo.is_excluded("1087 Amsterdam")       # IJburg
    # inner Oost stays (closer, kept) and nearby kept postcodes are unaffected
    assert geo.neighbourhood_tier("Oosterparkbuurt") == geo.BULLSEYE
    assert geo.neighbourhood_tier("Dapperbuurt") == geo.BULLSEYE
    assert geo.neighbourhood_tier("1093 Amsterdam") != geo.EXCLUDE      # inner Oost
    assert geo.neighbourhood_tier("1096DT Amsterdam") != geo.EXCLUDE    # Overamstel
    assert geo.neighbourhood_tier("1082 Amsterdam") != geo.EXCLUDE      # Buitenveldert (108x kept)


def test_more_non_target_cities_excluded():
    for c in ("Haarlem", "Almere", "Zaandam", "Purmerend", "Hilversum", "Aalsmeer", "Leiderdorp"):
        assert geo.is_excluded(c), c


def test_amsterdam_streets_not_false_excluded():
    # streets that merely start with an excluded city name must NOT be excluded
    assert not geo.is_excluded("Haarlemmerstraat")     # Amsterdam-centre street, not Haarlem
    assert not geo.is_excluded("Amstelveenseweg")      # Amsterdam-Zuid street, not Amstelveen
    assert not geo.is_excluded("Delftlaan")            # a street, not Delft
    assert geo.neighbourhood_tier("Hoofddorppleinbuurt") == geo.FINE  # not Hoofddorp town


def test_west_neighbourhood_tiers():
    # Oud-West sub-buurten are a top tier in the example preferences
    assert geo.neighbourhood_tier("Vondelparkbuurt") == geo.BULLSEYE
    assert geo.neighbourhood_tier("Helmersbuurt") == geo.BULLSEYE
    assert geo.neighbourhood_tier("Da Costabuurt") == geo.BULLSEYE
    assert geo.neighbourhood_tier("Kinkerbuurt") == geo.BULLSEYE
    assert geo.neighbourhood_tier("Westerpark") == geo.GREAT
    assert geo.neighbourhood_tier("Spaarndammerbuurt") == geo.GREAT
    assert geo.neighbourhood_tier("Frederik Hendrikbuurt") == geo.GREAT
    assert geo.neighbourhood_tier("Houthavens") == geo.FINE
    assert geo.neighbourhood_tier("Erasmuspark") == geo.FINE
    # rougher Bos en Lommer pockets kept but ranked down (Lower, not excluded)
    assert geo.neighbourhood_tier("Landlust") == geo.LOWER
    assert geo.neighbourhood_tier("Kolenkitbuurt") == geo.LOWER
    assert geo.neighbourhood_tier("Bos en Lommer") == geo.LOWER
    # Sloterdijk kept but ranked low (not excluded)
    assert geo.neighbourhood_tier("Sloterdijk") == geo.LOWER
    assert geo.neighbourhood_tier("Sloterdijk-Centrum") == geo.LOWER
    assert geo.neighbourhood_tier("Slotervaart") == geo.EXCLUDE   # still far-west excluded


def test_nieuw_west_area_and_street_names_excluded():
    # name-only catch (no network); accented names like Allebéplein are left to geocode
    for a in ("Slotermeer", "Overtoomse Veld", "De Aker", "Tussen Meer",
              "Meer en Vaart", "Osdorpplein", "Pieter Calandlaan"):
        assert geo.is_excluded(a), a


def test_west_no_false_excludes_from_new_names():
    # good central/West streets that merely resemble excluded names must NOT be excluded
    assert not geo.is_excluded("Overtoom")            # Oud-West main street, ≠ Overtoomse Veld
    assert not geo.is_excluded("Amstelveenseweg")     # ≠ any "...veld"/"...meer" token
    assert not geo.is_excluded("Spaarndammerstraat")  # good Westerpark street
    assert geo.neighbourhood_tier("IJmeer") is None   # bare "meer" must not exclude
    assert geo.neighbourhood_tier("De Akerstraat") is None  # right-boundary guards "de aker"


def test_nieuw_sloten_kept_over_postcode():
    # the one keep-worthy Nieuw-West pocket: a recognised good name beats its 106x postcode
    assert geo.neighbourhood_tier("Nieuw Sloten") == geo.FINE
    assert geo.neighbourhood_tier("Nieuw Sloten 1066AB Amsterdam") == geo.FINE
    assert not geo.is_excluded("Nieuw Sloten")
    # but a postcode-only 1066 listing (no name) stays excluded (far-SW default)
    assert geo.neighbourhood_tier("1066AB Amsterdam") == geo.EXCLUDE
    # the rest of Nieuw-West is unaffected
    assert geo.neighbourhood_tier("Slotermeer") == geo.EXCLUDE
    assert geo.neighbourhood_tier("1064 Amsterdam") == geo.EXCLUDE


def test_commuter_10min_ring_postcodes(commuters):
    # ~10-min-walk ring: the wider near-CS postcodes count as Fine
    assert geo.neighbourhood_tier("2011 JE Haarlem") == geo.FINE
    # but a far-from-CS postcode in that city is still excluded
    assert geo.neighbourhood_tier("2037 CS Haarlem") == geo.EXCLUDE
