import json
import sys
from .models import Listing, HousingType, Verdict
from .config import Config
from .classify import classify


def _housing_type(value):
    """Map a raw housing_type string to the enum; anything unknown → UNKNOWN."""
    try:
        return HousingType(value or "unknown")
    except ValueError:
        return HousingType.UNKNOWN


def _listing_from_dict(d):
    return Listing(
        source=d.get("source", ""), source_id=str(d.get("source_id", "")),
        url=d.get("url", ""), title=d.get("title", ""), description=d.get("description", ""),
        price_eur=d.get("price_eur"),
        housing_type=_housing_type(d.get("housing_type")),
        area=d.get("area"), available_from=d.get("available_from"),
        registration=d.get("registration"),
        is_sublet=bool(d.get("is_sublet", False)),
        is_woningruil=bool(d.get("is_woningruil", False)),
        max_income_eur=d.get("max_income_eur"),
        images=d.get("images", []), raw=d.get("raw", {}),
    )


def classify_file(path, config=None):
    config = config or Config()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return [classify(_listing_from_dict(d), config) for d in data]


def digest_from_store(store, limit=20):
    from .models import Verdict
    rows = store.recent(verdicts=(Verdict.SHOW.value, Verdict.FLAG.value),
                        exclude_status=("dismissed",), limit=limit)
    rows.sort(key=lambda r: (r.get("score") or 0), reverse=True)
    if not rows:
        return "No current listings."
    lines = [f"🏠 Today's shortlist ({len(rows)}):"]
    for r in rows:
        price = f"€{r['price_eur']}" if r.get("price_eur") else "€?"
        lines.append(f"[{r.get('score', 0)}] {r.get('title', '?')} - {price} - "
                     f"{r.get('area') or '?'}\n  {r.get('url', '')}")
    return "\n".join(lines)


def _print_decisions(decisions):
    shown = sorted([d for d in decisions if d.verdict in (Verdict.SHOW, Verdict.FLAG)],
                   key=lambda d: d.score, reverse=True)
    dropped = [d for d in decisions if d.verdict == Verdict.DROP]
    print(f"SHOW/FLAG: {len(shown)}   DROP: {len(dropped)}")
    for d in shown:
        tag = "FLAG" if d.verdict == Verdict.FLAG else "SHOW"
        print(f"[{d.score:3d}] {tag}  {d.listing.title}  - {d.listing.url}")
        print(f"        {' | '.join(d.reasons)}")
    print(f"\nDropped ({len(dropped)}):")
    for d in dropped:
        print(f"  - {d.listing.title}: {d.reasons[0]}")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: python -m home_hunt.cli <classify|scan|digest> [args]")
        return 2

    cmd, rest = argv[0], argv[1:]

    if cmd == "classify":
        if not rest:
            print("usage: python -m home_hunt.cli classify <listings.json>")
            return 2
        _print_decisions(classify_file(rest[0]))
        return 0

    if cmd == "scan":
        import os
        from .settings import Settings
        from .pipeline import scan
        from .budget import SpendGuard, current_month
        settings = Settings.from_env()
        sources = [] if "--no-sources" in rest else None
        spend_guard = SpendGuard.from_env()
        month = current_month()
        # commute refine is a paid Tier-3 browse - opt-in only (default off).
        commute_runner = None
        if os.environ.get("HOME_HUNT_COMMUTE") == "1":
            from .commute import _default_runner
            commute_runner = _default_runner
        # work-commute distance (free PDOK geocode + cache): on when HOME_HUNT_WORKSITE
        # is set, unless explicitly turned off.
        work_distance_fn = None
        if os.environ.get("HOME_HUNT_WORK_DISTANCE", "1") == "1":
            from .worksite import work_distance_km, worksite_latlon
            if worksite_latlon() is not None:
                work_distance_fn = work_distance_km
        # transit-to-work rescue/boost for bike-far listings - on unless explicitly off.
        transit_fn = None
        if os.environ.get("HOME_HUNT_TRANSIT", "1") == "1":
            from .transit import transit_for_area
            transit_fn = transit_for_area
        # read detail pages for hidden dealbreakers - on unless explicitly off.
        detail_fetcher = None
        if os.environ.get("HOME_HUNT_READ_DETAILS", "1") == "1":
            from .details import _default_fetch
            detail_fetcher = _default_fetch
        # street-name → district geocode (free PDOK) - on unless explicitly off.
        geocode_fn = None
        if os.environ.get("HOME_HUNT_GEOCODE", "1") == "1":
            from .worksite import geocode_postcode
            geocode_fn = geocode_postcode
        decisions = scan(settings, sources=sources, spend_guard=spend_guard,
                         month=month, commute_runner=commute_runner,
                         work_distance_fn=work_distance_fn, detail_fetcher=detail_fetcher,
                         geocode_fn=geocode_fn, transit_fn=transit_fn,
                         on_error=lambda name, exc: print(f"[source error] {name}: {exc}"))
        spend_guard.close()
        print(f"scanned: {len(decisions)} new listing(s) classified")
        return 0

    if cmd == "digest":
        from .settings import Settings
        from .store import Store
        from .notify import Notifier
        settings = Settings.from_env()
        store = Store(settings.db_path)
        Notifier(settings)._send(digest_from_store(store))
        store.close()
        return 0

    # back-compat: a bare path argument behaves like `classify <path>`
    if cmd.endswith(".json"):
        _print_decisions(classify_file(cmd))
        return 0

    print(f"unknown command: {cmd}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
