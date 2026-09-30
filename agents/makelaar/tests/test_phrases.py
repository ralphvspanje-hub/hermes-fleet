from home_hunt import phrases


def test_no_registration():
    assert phrases.has_no_registration("Leuke kamer, inschrijven niet mogelijk")
    assert phrases.has_no_registration("Sorry, no registration possible")
    assert not phrases.has_no_registration("Inschrijving mogelijk op dit adres")


def test_registration_ok():
    assert phrases.has_registration_ok("Inschrijving mogelijk")
    assert phrases.has_registration_ok("BRP registration allowed")


def test_sublet_and_woningruil_and_temporary():
    assert phrases.has_sublet("I am subletting my room")
    assert phrases.has_sublet("tijdelijke onderhuur aangeboden")
    assert phrases.has_woningruil("Woningruil aangeboden, 3-kamer")
    assert phrases.has_temporary("antikraak, short stay only")
    assert not phrases.has_sublet("Mooie studio te huur")


def test_short_term_and_date_range():
    assert phrases.has_short_term("Beschikbaar voor 2 maanden")
    assert phrases.has_short_term("max. 3 maanden")
    assert phrases.has_short_term("for 2 months only")
    assert phrases.has_short_term("For rent per 05-07-2026 until 05-09-2026")
    assert phrases.has_short_term("beschikbaar van 01-08-2026 tot 01-10-2026")
    assert phrases.has_temporary("Temporary available - nice flat")
    # NOT temporary: a minimum term or a single start date is a normal permanent let
    assert not phrases.has_short_term("minimaal 12 maanden, daarna onbepaalde tijd")
    assert not phrases.has_short_term("Beschikbaar per 01-08-2026")


def test_exclusion_phrases():
    assert phrases.has_women_only("Kamer te huur voor twee vrouwen")
    assert phrases.has_women_only("female only household")
    assert not phrases.has_women_only("geschikt voor vrouwen en mannen")  # mixed → not women-only
    assert phrases.has_student_only("students only, enrolment required")


def test_extract_max_income():
    assert phrases.extract_max_income("Maximaal inkomen €48.000 per jaar") == 48000
    assert phrases.extract_max_income("max income 51537") == 51537
    assert phrases.extract_max_income("Inkomen minimaal 3x de huur") is None
    assert phrases.extract_max_income("Mooie studio") is None


def test_max_income_monthly_is_annualized():
    # "income up to €4000/month" = €48k/yr (annualized); must NOT read as 4000
    assert phrases.extract_max_income("inkomen tot 4000 per maand") == 48000
    assert phrases.extract_max_income("max income 3000 p/m") == 36000


def test_max_income_ignores_tiny_and_keeps_high_caps():
    assert phrases.extract_max_income("inkomensgrens 70149") == 70149   # real middenhuur cap, kept
    assert phrases.extract_max_income("max inkomen 1500") is None        # too small to be an annual cap
