import pytest
from home_hunt.email_parsers.base import EmailParser
from home_hunt.models import Listing, HousingType


class _FakePortal(EmailParser):
    name = "fake_portal"
    senders = ("fake-portal.example", "alerts.fake")

    def parse(self, html, subject=""):
        return [Listing(source="fake_portal", source_id="1", url="https://fake-portal.example/x",
                        title="Studio", description=html[:20], price_eur=1200,
                        housing_type=HousingType.SOLO, area="De Pijp")]


def test_matches_is_case_insensitive_substring():
    p = _FakePortal()
    assert p.matches("Alerts <noreply@fake-portal.example>") is True
    assert p.matches("X <noreply@ALERTS.FAKE>") is True
    assert p.matches("noreply@somewhere-else.com") is False
    assert p.matches(None) is False


def test_base_parse_is_abstract():
    with pytest.raises(NotImplementedError):
        EmailParser().parse("<html></html>")


def test_subclass_parse_returns_listings():
    out = _FakePortal().parse("<html>body</html>", "subj")
    assert len(out) == 1 and out[0].source == "fake_portal"
