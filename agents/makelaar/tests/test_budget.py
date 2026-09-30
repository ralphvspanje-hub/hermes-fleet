import datetime
from home_hunt.budget import SpendGuard, current_month, monthly_cap


def test_records_and_caps(tmp_path):
    g = SpendGuard(str(tmp_path / "b.sqlite"), monthly_cap_eur=50)
    assert g.spent("2026-06") == 0
    assert g.can_run("2026-06", est_eur=1.0) is True
    for _ in range(40):
        g.record("2026-06", 1.0)               # €40 spent
    assert round(g.spent("2026-06"), 2) == 40.0
    assert g.can_run("2026-06", est_eur=5.0) is True     # 40+5 ≤ 50
    assert g.can_run("2026-06", est_eur=15.0) is False   # 40+15 > 50
    assert g.spent("2026-07") == 0                        # per-month isolation


def test_current_month_defaults_to_today_not_empty():
    today = datetime.date(2030, 3, 9)
    assert current_month(env={}, today=today) == "2030-03"
    assert current_month(env={"HOME_HUNT_MONTH": ""}, today=today) == "2030-03"
    assert current_month(env={"HOME_HUNT_MONTH": "2030-01"}, today=today) == "2030-01"
    assert current_month(env={}) != ""


def test_monthly_cap_from_env(tmp_path):
    assert monthly_cap(env={}) == 50
    assert monthly_cap(env={"HOME_HUNT_MONTHLY_CAP": "20"}) == 20
    assert monthly_cap(env={"HOME_HUNT_MONTHLY_CAP": "lots"}) == 50
    g = SpendGuard.from_env(env={"HOME_HUNT_BUDGET_DB": str(tmp_path / "b.sqlite"),
                                 "HOME_HUNT_MONTHLY_CAP": "10"})
    assert g.cap == 10
    g.close()
