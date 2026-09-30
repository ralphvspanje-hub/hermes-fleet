from home_hunt.draft import draft_intro, build_prompt, DEFAULT_PROFILE
from home_hunt.models import Listing, HousingType


def _l(**kw):
    base = dict(source="t", source_id="1", url="u", title="Studio De Pijp",
                description="Lichte studio, skiing-loving neighbours", price_eur=1150,
                housing_type=HousingType.SOLO, area="De Pijp")
    base.update(kw)
    return Listing(**base)


class _FakeMessages:
    def __init__(self, captured):
        self.captured = captured

    def create(self, **kwargs):
        self.captured.update(kwargs)
        class _R:
            content = [type("B", (), {"text": "Hee! Ik ben Sam..."})()]
        return _R()


class _FakeClient:
    def __init__(self):
        self.captured = {}
        self.messages = _FakeMessages(self.captured)


def test_build_prompt_includes_facts_and_listing():
    p = build_prompt(_l(), DEFAULT_PROFILE)
    assert "YOUR_SITUATION" in p and "YOUR_INTERESTS" in p   # profile facts injected
    assert "Studio De Pijp" in p          # listing context is injected


def test_build_prompt_handles_missing_age():
    p = build_prompt(_l(), DEFAULT_PROFILE)          # default age is None
    assert "None" not in p and "()" not in p
    assert "YOUR_NAME;" in p


def test_build_prompt_includes_age_when_given():
    profile = dict(DEFAULT_PROFILE, name="Sam", age=30)
    assert "Sam (30);" in build_prompt(_l(), profile)


def test_draft_intro_uses_client_and_returns_text():
    client = _FakeClient()
    out = draft_intro(_l(), client=client, model="claude-sonnet-5")
    assert out == "Hee! Ik ben Sam..."
    assert client.captured["model"] == "claude-sonnet-5"
    assert client.captured["max_tokens"] > 0
