from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Tunable decision thresholds (runtime I/O settings live in settings.py)."""
    # example values, tune for your market
    solo_max_eur: int = 1500        # ceiling for a solo studio/1-bed
    shared_max_eur: int = 1000      # ceiling for a (top-tier) shared room
    middenhuur_max_eur: int = 1228  # at/below this = ranked highest
    income_eur: int = 0             # your gross yearly income; 0 disables the income filter
    allow_shared: bool = False      # shared/room listings off by default (no shared spam)
    max_commute_km: float = 7.5     # drop listings > this straight-line km from the worksite
    # Optional household exclusions, off by default. Available tags (see filters.py):
    #   "women_only"   - drop listings for a women-only household
    #   "student_only" - drop listings restricted to students
    exclude_household_tags: tuple = ()
