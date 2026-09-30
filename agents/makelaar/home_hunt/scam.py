"""Light scam check (official sites are clean; this catches the odd direct-landlord ad)."""

_REJECT = (
    "pay the deposit to secure", "betaal de borg", "borg vooraf", "deposit before",
    "transfer to confirm", "betaling om te reserveren", "western union", "moneygram",
    "gift card", "bitcoin", "crypto", "send the keys", "sleutels worden opgestuurd",
    "keys by dhl",
)
_FLAG = (
    "geen bezichtiging", "no viewing", "bezichtiging pas na betaling",
    "whatsapp", "telegram", "app me op", "high demand", "snel beslissen", "decide today",
)


def assess(listing):
    """Return (tier, flags). tier ∈ {'reject', 'flag', 'none'}."""
    t = f"{listing.title} {listing.description}".lower()
    reject = [w for w in _REJECT if w in t]
    if reject:
        return "reject", reject
    flag = [w for w in _FLAG if w in t]
    if flag:
        return "flag", flag
    return "none", []
