from home_hunt.config import Config


def test_defaults():
    c = Config()
    assert c.solo_max_eur == 1500
    assert c.shared_max_eur == 1000
    assert c.middenhuur_max_eur == 1228
    assert c.income_eur == 0          # income filter disabled by default
