"""Monthly spend guard for the paid (Tier-3 computer-use) layer. SpendGuard itself is
pure: the caller passes the month key 'YYYY-MM'. The env helpers below resolve the
month, cap, and database path for live runs."""
import datetime
import os
import sqlite3

DEFAULT_MONTHLY_CAP_EUR = 50


def current_month(env=None, today=None):
    """HOME_HUNT_MONTH if set, else today's 'YYYY-MM' (never '' - an empty key would
    only ever sum rows recorded under '', silently under-reporting spend)."""
    env = env if env is not None else os.environ
    month = (env.get("HOME_HUNT_MONTH") or "").strip()
    return month or (today or datetime.date.today()).strftime("%Y-%m")


def monthly_cap(env=None):
    """HOME_HUNT_MONTHLY_CAP in EUR (default 50); a malformed value falls back to 50."""
    env = env if env is not None else os.environ
    try:
        return float(env.get("HOME_HUNT_MONTHLY_CAP", DEFAULT_MONTHLY_CAP_EUR))
    except ValueError:
        return DEFAULT_MONTHLY_CAP_EUR


class SpendGuard:
    def __init__(self, path, monthly_cap_eur=50):
        self.cap = monthly_cap_eur
        self.conn = sqlite3.connect(path)
        self.conn.execute(
            "CREATE TABLE IF NOT EXISTS spend (month TEXT, eur REAL, ts TEXT)")
        self.conn.commit()

    def spent(self, month):
        row = self.conn.execute(
            "SELECT COALESCE(SUM(eur),0) FROM spend WHERE month=?", (month,)).fetchone()
        return row[0] or 0.0

    def record(self, month, eur, ts=""):
        self.conn.execute("INSERT INTO spend (month, eur, ts) VALUES (?,?,?)",
                          (month, float(eur), ts))
        self.conn.commit()

    def can_run(self, month, est_eur):
        return (self.spent(month) + float(est_eur)) <= self.cap

    def close(self):
        self.conn.close()

    @classmethod
    def from_env(cls, env=None):
        """Guard on HOME_HUNT_BUDGET_DB with the HOME_HUNT_MONTHLY_CAP cap."""
        env = env if env is not None else os.environ
        return cls(env.get("HOME_HUNT_BUDGET_DB", "home_hunt_budget.sqlite"),
                   monthly_cap_eur=monthly_cap(env))
