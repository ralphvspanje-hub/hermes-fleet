from pathlib import Path
from home_hunt.sources.browse_json import listings_from_browse_json, BrowseSource
from home_hunt.models import HousingType

FIX = str(Path(__file__).parent / "fixtures" / "browse_out.json")


def test_browse_json_maps_to_listings():
    out = listings_from_browse_json(FIX)
    assert len(out) == 1
    l = out[0]
    assert l.source == "example" and l.source_id == "b123"
    assert l.housing_type == HousingType.SHARED
    assert l.price_eur == 850 and l.registration is True


def test_browse_json_defaults_source_from_doc(tmp_path):
    # a listing without its own "source" inherits the document-level source
    p = tmp_path / "out.json"
    p.write_text('{"source": "example", "listings": [{"source_id": "x", "url": "u",'
                 ' "title": "t", "price_eur": 700, "housing_type": "shared"}]}',
                 encoding="utf-8")
    out = listings_from_browse_json(str(p))
    assert out[0].source == "example"


def test_browse_source_uses_injected_runner(tmp_path):
    out = tmp_path / "out.json"
    out.write_text('{"source":"example","listings":[{"source_id":"b9","url":"u",'
                   '"title":"Room","price_eur":800,"housing_type":"shared","registration":true}]}',
                   encoding="utf-8")
    src = BrowseSource(runner=lambda: str(out))
    listings = src.fetch()
    assert [l.source for l in listings] == ["example"]
    assert listings[0].source_id == "b9"


def test_browse_source_empty_on_missing_output():
    src = BrowseSource(runner=lambda: "")     # engine produced nothing
    assert src.fetch() == []


def test_unknown_housing_type_falls_back_to_unknown(tmp_path):
    p = tmp_path / "out.json"
    p.write_text('{"source": "example", "listings": [{"source_id": "x", "url": "u",'
                 ' "title": "t", "price_eur": 900, "housing_type": "penthouse"}]}',
                 encoding="utf-8")
    assert listings_from_browse_json(str(p))[0].housing_type == HousingType.UNKNOWN
