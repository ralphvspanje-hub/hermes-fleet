from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class HousingType(str, Enum):
    SOLO = "solo"        # studio / 1-bed / self-contained
    SHARED = "shared"    # room in a shared house
    UNKNOWN = "unknown"


class Verdict(str, Enum):
    SHOW = "show"
    FLAG = "flag"        # shown, but flagged (uncertain / light scam)
    DROP = "drop"


@dataclass
class Listing:
    source: str
    source_id: str
    url: str
    title: str
    description: str
    price_eur: Optional[int]              # base rent €/month (None = unknown)
    housing_type: HousingType
    area: Optional[str] = None            # neighbourhood/area string as scraped
    available_from: Optional[str] = None  # raw text or ISO date
    registration: Optional[bool] = None   # True / False / None (unknown)
    is_sublet: bool = False
    is_woningruil: bool = False
    max_income_eur: Optional[int] = None  # stated MAX income cap, if any
    images: list = field(default_factory=list)
    raw: dict = field(default_factory=dict)
