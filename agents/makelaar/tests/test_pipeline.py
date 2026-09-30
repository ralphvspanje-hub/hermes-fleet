from home_hunt.pipeline import scan
from home_hunt.settings import Settings
from home_hunt.store import Store
from home_hunt.models import Listing, HousingType, Verdict


class _StubSource:
    name = "stub"

    def __init__(self, listings):
        self._listings = listings

    def fetch(self):
        return self._listings


class _Capture:
    def __init__(self):
        self.instants = []
        self.digests = []

    def instant(self, decision, draft=""):
        self.instants.append((decision, draft))

    def digest(self, decisions, hidden_count=0):
        self.digests.append((decisions, hidden_count))


def _listing(source_id, **kw):
    base = dict(source="stub", source_id=source_id, url="u" + source_id, title="Studio",
                description="", price_eur=1100, housing_type=HousingType.SOLO,
                area="De Pijp", registration=True)
    base.update(kw)
    return Listing(**base)


def test_scan_classifies_notifies_and_dedupes(tmp_path):
    store = Store(str(tmp_path / "s.sqlite"))
    cap = _Capture()
    good = _listing("1")
    dropped = _listing("2", is_sublet=True)            # hard-drop → no ping
    src = _StubSource([good, dropped])

    decisions = scan(Settings(), store=store, notifier=cap, sources=[src],
                     draft_fn=lambda l: "DRAFT", ts="2026-06-24")
    assert len(decisions) == 2
    assert len(cap.instants) == 1                       # only the SHOW pinged
    assert cap.instants[0][1] == "DRAFT"

    # second scan: both already seen → nothing new, no pings
    cap2 = _Capture()
    again = scan(Settings(), store=store, notifier=cap2, sources=[src],
                 draft_fn=lambda l: "DRAFT", ts="2026-06-24")
    assert again == []
    assert cap2.instants == []
    store.close()


def test_scan_dedupes_within_one_run(tmp_path):
    store = Store(str(tmp_path / "s.sqlite"))
    cap = _Capture()
    # same (source, source_id) twice in one batch (a repeated alert card) → one ping
    src = _StubSource([_listing("dup"), _listing("dup")])
    decisions = scan(Settings(), store=store, notifier=cap, sources=[src],
                     draft_fn=lambda l: "D", ts="t")
    assert len(decisions) == 1
    assert len(cap.instants) == 1
    store.close()


def test_failing_source_is_isolated(tmp_path):
    store = Store(str(tmp_path / "s.sqlite"))

    class _Boom:
        name = "boom"
        def fetch(self):
            raise RuntimeError("blocked")

    cap = _Capture()
    decisions = scan(Settings(), store=store, notifier=cap,
                     sources=[_Boom(), _StubSource([_listing("9")])],
                     draft_fn=lambda l: "", ts="t")
    assert len(decisions) == 1                          # the good source still ran
    store.close()


def test_scan_spend_guard_skips_paid_source(tmp_path):
    store = Store(str(tmp_path / "s.sqlite"))
    cap = _Capture()

    class _PaidSource:
        name = "paid"
        est_cost_eur = 10.0
        def fetch(self):
            raise AssertionError("must not fetch a paid source when the cap is hit")

    class _CapHit:
        def can_run(self, month, est_eur):
            return False
        def record(self, *a, **k):
            raise AssertionError("must not record when the source was skipped")

    skipped = []
    decisions = scan(Settings(), store=store, notifier=cap,
                     sources=[_PaidSource(), _StubSource([_listing("9")])],
                     draft_fn=lambda l: "D", ts="t",
                     spend_guard=_CapHit(), month="2026-06",
                     on_error=lambda name, exc: skipped.append(name))
    assert len(decisions) == 1            # only the free source ran
    assert "paid" in skipped
    store.close()


def test_scan_paid_source_runs_and_records_under_cap(tmp_path):
    store = Store(str(tmp_path / "s.sqlite"))
    cap = _Capture()
    recorded = []

    class _Guard:
        def can_run(self, month, est_eur):
            return True
        def record(self, month, eur, ts=""):
            recorded.append((month, eur))

    class _PaidSource:
        name = "paid"
        est_cost_eur = 5.0
        def fetch(self):
            return [_listing("p1")]

    decisions = scan(Settings(), store=store, notifier=cap, sources=[_PaidSource()],
                     draft_fn=lambda l: "D", ts="t", spend_guard=_Guard(), month="2026-06")
    assert len(decisions) == 1
    assert recorded == [("2026-06", 5.0)]
    store.close()


def test_scan_commute_drops_far_commuter_city_before_notifying(tmp_path, commuter_example):
    store = Store(str(tmp_path / "s.sqlite"))
    cap = _Capture()
    near_cs = _listing("u1", area="2011 Haarlem")     # near-CS postcode → FINE → SHOW
    decisions = scan(Settings(), store=store, notifier=cap,
                     sources=[_StubSource([near_cs])],
                     draft_fn=lambda l: "D", ts="t",
                     commute_runner=lambda addr: {"verdict": False, "minutes": 20})
    by = {d.listing.source_id: d for d in decisions}
    assert by["u1"].verdict == Verdict.DROP           # confirmed far → dropped
    assert cap.instants == []                          # and NOT pinged
    store.close()


def test_scan_geocode_drops_excluded_district_street_only(tmp_path):
    store = Store(str(tmp_path / "s.sqlite"))
    cap = _Capture()
    # area=None, only a Nieuw-West street in the title → would classify SHOW, but the
    # geocode refine resolves it to an excluded district and drops it before notifying.
    street_only = _listing("nw1", area=None, title="Studio August Allebeplein")
    decisions = scan(Settings(), store=store, notifier=cap,
                     sources=[_StubSource([street_only])],
                     draft_fn=lambda l: "D", ts="t",
                     geocode_fn=lambda text: "1062AA")
    by = {d.listing.source_id: d for d in decisions}
    assert by["nw1"].verdict == Verdict.DROP
    assert cap.instants == []                          # not pinged
    store.close()


def test_scan_transit_rescues_bikefar_listing(tmp_path):
    store = Store(str(tmp_path / "s.sqlite"))
    cap = _Capture()
    far = _listing("t1", area="1051 Amsterdam")        # kept area, made bike-far via stub
    decisions = scan(Settings(), store=store, notifier=cap, sources=[_StubSource([far])],
                     draft_fn=lambda l: "D", ts="t",
                     work_distance_fn=lambda a: 9.0,    # bike-far
                     transit_fn=lambda a: ("Sloterdijk (M50+rail)", 14, 400.0))
    by = {d.listing.source_id: d for d in decisions}
    assert by["t1"].verdict in (Verdict.SHOW, Verdict.FLAG)   # rescued, not dropped
    assert len(cap.instants) == 1                            # and still pinged
    store.close()

