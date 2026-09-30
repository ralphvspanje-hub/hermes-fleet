from home_hunt.models import Listing, HousingType, Verdict
from home_hunt.config import Config
from home_hunt.classify import classify, Decision

CFG = Config()


def _l(**kw):
    base = dict(source="t", source_id="1", url="u", title="", description="",
                price_eur=1100, housing_type=HousingType.SOLO, area="De Pijp",
                registration=True)
    base.update(kw)
    return Listing(**base)


def test_clean_listing_is_shown_with_score():
    d = classify(_l(), CFG)
    assert isinstance(d, Decision)
    assert d.verdict == Verdict.SHOW
    assert d.score > 0


def test_hard_drop_short_circuits():
    d = classify(_l(is_sublet=True), CFG)
    assert d.verdict == Verdict.DROP
    assert d.score == 0
    assert d.reasons == ["sublet/onderhuur"]


def test_reject_scam_drops():
    d = classify(_l(description="pay the deposit to secure via bitcoin"), CFG)
    assert d.verdict == Verdict.DROP
    assert d.scam_flags


def test_soft_scam_flags_but_shows():
    d = classify(_l(description="message me on whatsapp"), CFG)
    assert d.verdict == Verdict.FLAG
    assert d.score > 0
