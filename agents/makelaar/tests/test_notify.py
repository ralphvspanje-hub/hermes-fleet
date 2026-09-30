from home_hunt.notify import Notifier, format_card, format_digest
from home_hunt.settings import Settings
from home_hunt.classify import classify
from home_hunt.config import Config
from home_hunt.models import Listing, HousingType, Verdict


def _d(source_id="1", area="De Pijp"):
    l = Listing(source="example", source_id=source_id, url="https://x/" + source_id,
                title="Studio", description="", price_eur=1100,
                housing_type=HousingType.SOLO, area=area, registration=True)
    return classify(l, Config())


class _FakePoster:
    def __init__(self):
        self.calls = []

    def __call__(self, token, method, payload):
        self.calls.append((token, method, payload))
        return {"ok": True}


def test_format_card_has_score_link_and_draft():
    text = format_card(_d(), draft="Hee! Ik ben Sam...")
    assert "https://x/1" in text
    assert "1100" in text or "€1100" in text
    assert "Hee! Ik ben Sam" in text


def test_instant_posts_sendmessage():
    poster = _FakePoster()
    n = Notifier(Settings(telegram_bot_token="tok", telegram_chat_id="555"), poster=poster)
    n.instant(_d(), draft="hi")
    assert len(poster.calls) == 1
    token, method, payload = poster.calls[0]
    assert token == "tok" and method == "sendMessage"
    assert payload["chat_id"] == "555"


def test_long_text_is_split_under_4096():
    poster = _FakePoster()
    n = Notifier(Settings(telegram_bot_token="t", telegram_chat_id="5"), poster=poster)
    n._send("x" * 9000)                         # 3 chunks
    assert len(poster.calls) == 3
    assert all(len(c[2]["text"]) <= 4096 for c in poster.calls)


def test_split_never_cuts_a_url_across_messages():
    from home_hunt.notify import _chunks, _TG_LIMIT
    url = "https://example.com/listing/amsterdam-1011aa-1-" + "a" * 70
    text = ("x" * (_TG_LIMIT - 15)) + "\n" + url + "\nmore text"   # url straddles the 4096 boundary
    chunks = _chunks(text)
    assert all(len(c) <= _TG_LIMIT for c in chunks)
    assert any(url in c for c in chunks), "URL must stay intact in one message"


def test_digest_with_many_listings_keeps_every_url_whole():
    from home_hunt.notify import _chunks, _TG_LIMIT
    ds = [_d(str(i)) for i in range(120)]          # big digest, will exceed 4096
    text = format_digest(ds)
    chunks = _chunks(text)
    assert len(chunks) > 1 and all(len(c) <= _TG_LIMIT for c in chunks)
    for d in ds:                                    # every listing url survives intact somewhere
        assert any(d.listing.url in c for c in chunks)


def test_digest_lists_ranked_and_tally():
    text = format_digest([_d("1"), _d("2")], hidden_count=4)
    assert "2" in text                          # count of matches
    assert "4" in text                          # "N filtered" tally
