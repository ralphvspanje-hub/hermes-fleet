from home_hunt.models import Listing, HousingType, Verdict


def test_listing_defaults_and_enums():
    l = Listing(
        source="example", source_id="abc", url="https://x", title="Studio",
        description="Nice studio", price_eur=1400, housing_type=HousingType.SOLO,
        area="De Pijp", available_from="2026-08-01", registration=True,
    )
    assert l.is_sublet is False
    assert l.is_woningruil is False
    assert l.max_income_eur is None
    assert l.images == [] and l.raw == {}
    assert HousingType.SOLO.value == "solo"
    assert Verdict.DROP.value == "drop"
