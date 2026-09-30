import json
from pathlib import Path
from home_hunt.cli import classify_file
from home_hunt.models import Verdict

FIX = Path(__file__).parent / "fixtures" / "calibration.json"


def test_calibration_regression():
    by_id = {d.listing.source_id: d for d in classify_file(str(FIX))}
    # genuine but breaks hard rules → dropped
    assert by_id["sublet_room"].verdict == Verdict.DROP
    assert by_id["sublet_room"].reasons[0] == "no registration"  # pin which rule fires (it also trips sublet + over-budget)
    assert by_id["noreg"].verdict == Verdict.DROP
    assert by_id["swap"].verdict == Verdict.DROP
    assert by_id["swap"].reasons[0].startswith("woningruil")
    # the clean one → shown
    assert by_id["good"].verdict == Verdict.SHOW
    assert by_id["good"].score > 0
