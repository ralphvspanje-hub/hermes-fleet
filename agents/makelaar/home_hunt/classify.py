from dataclasses import dataclass, field
from .models import Listing, Verdict
from . import filters, scam, scoring


@dataclass
class Decision:
    listing: Listing
    verdict: Verdict
    score: int
    reasons: list = field(default_factory=list)
    scam_flags: list = field(default_factory=list)


def classify(listing: Listing, config) -> Decision:
    drop = filters.hard_drop_reason(listing, config)
    if drop:
        return Decision(listing, Verdict.DROP, 0, [drop], [])

    tier, flags = scam.assess(listing)
    if tier == "reject":
        return Decision(listing, Verdict.DROP, 0, [f"scam: {', '.join(flags)}"], flags)

    pts, why = scoring.score(listing, config)
    reasons = [why]
    verdict = Verdict.SHOW
    if tier == "flag":
        verdict = Verdict.FLAG
        reasons.append(f"⚠️ possible scam: {', '.join(flags)}")
    return Decision(listing, verdict, pts, reasons, flags)
