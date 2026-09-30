from home_hunt.store import Store
from home_hunt.classify import classify
from home_hunt.config import Config
from home_hunt.models import Listing, HousingType


def _decision(source_id, area="De Pijp"):
    l = Listing(source="t", source_id=source_id, url="u", title="Studio", description="",
                price_eur=1100, housing_type=HousingType.SOLO, area=area, registration=True)
    return classify(l, Config())


def test_seen_record_and_mark(tmp_path):
    db = str(tmp_path / "t.sqlite")
    store = Store(db)
    assert store.seen("t", "1") is False
    store.record(_decision("1"), ts="2026-06-24")
    assert store.seen("t", "1") is True
    assert store.seen("t", "2") is False                 # different id
    store.mark("t", "1", "contacted")
    assert store.status("t", "1") == "contacted"
    store.close()


def test_record_is_idempotent(tmp_path):
    db = str(tmp_path / "t.sqlite")
    store = Store(db)
    store.record(_decision("1"), ts="2026-06-24")
    store.record(_decision("1"), ts="2026-06-24")        # INSERT OR IGNORE
    assert store.count() == 1
    store.close()
