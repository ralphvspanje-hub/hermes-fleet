from pathlib import Path
from home_hunt.email_parsers.generic import GenericEmail

FIX = (Path(__file__).parent / "fixtures" / "email" / "generic_alert.html").read_text(encoding="utf-8")


def test_generic_extracts_links_and_prices():
    out = GenericEmail(source="example", senders=("example.com",)).parse(FIX)
    assert len(out) == 2
    assert out[0].source == "example"
    assert out[0].url.startswith("http")
    assert out[0].price_eur == 1150


def test_generic_price_not_bled_into_following_number():
    html = ('<div class="listing">'
            '<a href="https://example.com/huurwoning/amsterdam/55021/voorbeeldstraat">Studio</a>'
            '<span>&euro; 1.150</span> 1093 Amsterdam 60 m2</div>')
    out = GenericEmail(source="example", senders=("example.com",)).parse(html)
    assert out[0].price_eur == 1150


def test_generic_keeps_distinct_listings_sharing_a_slug():
    # two different listings whose URLs end in the same slug must both survive
    html = ('<div class="listing"><a href="https://example.net/a/100/studio">A</a><span>&euro; 1.100 p/m</span></div>'
            '<div class="listing"><a href="https://example.net/b/200/studio">B</a><span>&euro; 1.200 p/m</span></div>')
    out = GenericEmail(source="x", senders=("example.net",)).parse(html)
    assert len(out) == 2


def test_generic_skips_links_without_a_price():
    # disclaimer / homepage / tracking links have no price → not listings
    html = ('<div><a href="https://www.example.org/nl/disclaimer">Disclaimer</a></div>'
            '<div><a href="https://www.example.org">www.example.org</a></div>'
            '<div><a href="http://track.example.org/ls/click?upn=abc">/ls/click</a></div>'
            '<div class="listing"><a href="https://www.example.org/nl/unit/amsterdam/de-pijp-123">'
            'Studio De Pijp</a><span>&euro; 1.250 p/m</span></div>')
    out = GenericEmail(source="example", senders=("example.org",)).parse(html)
    assert [l.url for l in out] == ["https://www.example.org/nl/unit/amsterdam/de-pijp-123"]
    assert out[0].price_eur == 1250


def test_generic_skips_boilerplate_links():
    html = ('<div class="listing"><a href="https://example.com/huurwoning/amsterdam/77001/studio-x">Studio X</a>'
            '<span>&euro; 1.200 p/m</span></div>'
            '<a href="https://example.com/account/afmelden">Unsubscribe</a>')
    out = GenericEmail(source="example", senders=("example.com",)).parse(html)
    assert len(out) == 1
    assert out[0].url.endswith("/studio-x")
