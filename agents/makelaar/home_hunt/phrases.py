"""NL + EN phrase detection for the filter engine."""
import re

_NO_REGISTRATION = (
    "geen inschrijving", "inschrijven niet mogelijk", "inschrijving niet mogelijk",
    "registratie niet mogelijk", "geen brp", "gba niet mogelijk",
    "inschrijven helaas niet mogelijk", "no registration", "registration not possible",
    "cannot register", "no brp",
)
_REGISTRATION_OK = (
    "inschrijving mogelijk", "inschrijven mogelijk", "gba mogelijk",
    "huurcontract op naam", "registration possible", "brp registration allowed",
    "you can register",
)
_SUBLET = ("onderhuur", "onderverhuur", "tijdelijke onderhuur", "sublet", "subletting", "sublease")
_WONINGRUIL = ("woningruil", "woning ruil", "ruilwoning")
_TEMPORARY = (
    "antikraak", "anti-kraak", "anti kraak", "short stay", "shortstay",
    "tijdelijke huur", "tijdelijke verhuur", "tussenhuur", "vakantieverhuur",
    "campuscontract", "studentencontract", "temporary", "temporarily", "tijdelijk",
)
# A SHORT fixed lease (≤7 months) stated as a max/availability - e.g. "voor 2 maanden",
# "max. 3 maanden", "for 2 months". Deliberately does NOT match a MINIMUM term like
# "ten minste 12 maanden" / "minimaal 12 maanden" (those are good long leases).
_SHORT_TERM = re.compile(
    r"(?:max(?:imaal|imum)?\.?|slechts|alleen|enkel|voor|beschikbaar voor|"
    r"huurperiode\s*(?:van\s*)?|periode van|for|only)\s*([1-7])\s*"
    r"(?:maanden|maand|months?|mnd)\b",
    re.IGNORECASE,
)
# A fixed start→end date range ("per 05-07-2026 until 05-09-2026", "van … tot …")
# = a fixed-term/temporary let (a permanent rental states only a start date).
_DATE = r"\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}"
_DATE_RANGE = re.compile(
    rf"(?:per|from|van|vanaf)\s*{_DATE}\b.{{0,18}}?\b(?:until|tot en met|tot|t/m|to)\b\s*{_DATE}",
    re.IGNORECASE,
)


def _has_any(text, needles):
    t = (text or "").lower()
    return any(n in t for n in needles)


# Already gone - reserved / let / off-market. "gereserveerd" / "onder optie" are
# reliable status words; for "verhuurd" we require a status-style usage (title
# "Verhuurd: <addr>", "reeds/al/is verhuurd") so we don't trip on agency boilerplate
# like "heeft ruim woningen verhuurd". Bare English "reserved" is excluded on purpose
# (it appears in "all rights reserved" footers).
_UNAVAILABLE = (
    "gereserveerd", "onder optie", "reeds verhuurd", "al verhuurd", "is verhuurd",
    "verhuurd:", "woning verhuurd", "reeds verkocht", "niet meer beschikbaar",
    "niet langer beschikbaar", "no longer available", "already rented", "under offer",
)


def has_unavailable(text): return _has_any(text, _UNAVAILABLE)
def has_no_registration(text): return _has_any(text, _NO_REGISTRATION)
def has_registration_ok(text): return _has_any(text, _REGISTRATION_OK)
def has_sublet(text): return _has_any(text, _SUBLET)
def has_woningruil(text): return _has_any(text, _WONINGRUIL)
def has_temporary(text): return _has_any(text, _TEMPORARY)
def has_short_term(text):
    t = text or ""
    return _SHORT_TERM.search(t) is not None or _DATE_RANGE.search(t) is not None


# women-only: require explicit "only"-style phrasing to avoid matching mixed houses
_WOMEN_ONLY = (
    "alleen voor vrouwen", "alleen vrouwen", "voor twee vrouwen", "voor een vrouw",
    "women only", "female only", "only girls", "girls only",
)
_STUDENT_ONLY = ("alleen studenten", "students only", "only students", "student only")

_MAX_INCOME = re.compile(
    r"(?:max(?:imaal|imum)?\s*inkomen|inkomen\s*tot|inkomensgrens|maximum\s*income|max\.?\s*income)"
    r"[^\d€]{0,20}€?\s*([\d.,]{3,})",
    re.IGNORECASE,
)
_MIN_CREDIBLE_ANNUAL_CAP = 20000  # below this, a captured number is a monthly figure or a min-multiple, not an annual cap


def has_women_only(text): return _has_any(text, _WOMEN_ONLY)
def has_student_only(text): return _has_any(text, _STUDENT_ONLY)


def extract_max_income(text):
    """Return the stated MAX income in €/year if present, else None.

    Annualizes figures stated per month, and ignores values too small to be a
    credible annual income cap (almost always a monthly figure or a 'X× the rent'
    minimum) - we never hard-drop on those, biasing toward showing."""
    m = _MAX_INCOME.search(text or "")
    if not m:
        return None
    digits = m.group(1).replace(".", "").replace(",", "").replace(" ", "")
    try:
        val = int(digits)
    except ValueError:
        return None
    tail = (text or "").lower()[m.end():m.end() + 15]
    if any(k in tail for k in ("maand", "mnd", "p/m", "per month", "month")):
        val *= 12  # stated per month → annualize
    return val if val >= _MIN_CREDIBLE_ANNUAL_CAP else None
