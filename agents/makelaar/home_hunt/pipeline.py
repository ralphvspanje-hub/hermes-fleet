"""One scan cycle: fetch → dedupe → classify → (commute-refine) → store → ping.
All I/O collaborators are injectable so the cycle is fully unit-tested.

Paid (Tier-3) sources - those with `est_cost_eur > 0` - run only while the optional
SpendGuard says the monthly budget allows it. Commute refinement (the optional
commuter-city ≤10-min-walk map check) runs before notifying, so a confirmed-too-far listing is
dropped rather than pinged; it is opt-in via `commute_runner`."""
from .classify import classify
from .commute import refine_commute_listings
from .worksite import refine_work_distance, refine_geo_geocode
from .details import refine_with_details
from .config import Config
from .models import Verdict
from .sources.base import get_enabled
from .store import Store
from .notify import Notifier


def scan(settings, config=None, store=None, notifier=None, sources=None,
         draft_fn=None, ts="", on_error=None,
         spend_guard=None, month="", commute_runner=None, work_distance_fn=None,
         detail_fetcher=None, geocode_fn=None, transit_fn=None):
    config = config or Config()
    store = store or Store(settings.db_path)
    notifier = notifier or Notifier(settings)
    sources = sources if sources is not None else get_enabled(settings)

    new_decisions = []
    seen_now = set()           # de-dupe within this run (record happens later, below)
    for src in sources:
        est = getattr(src, "est_cost_eur", 0.0)
        if est and spend_guard is not None and not spend_guard.can_run(month, est):
            if on_error:
                on_error(getattr(src, "name", "?"),
                         RuntimeError("monthly spend cap reached; source skipped"))
            continue
        try:
            listings = src.fetch()
        except Exception as exc:                         # loud-but-isolated failure
            if on_error:
                on_error(getattr(src, "name", "?"), exc)
            continue
        if est and spend_guard is not None:
            spend_guard.record(month, est, ts)
        for listing in listings:
            key = (listing.source, str(listing.source_id))
            if key in seen_now or store.seen(listing.source, listing.source_id):
                continue
            seen_now.add(key)
            new_decisions.append(classify(listing, config))

    # Work-commute refine (opt-in via work_distance_fn): drop listings too far to
    # bike to the worksite; nudge the rest so closer-to-work ranks higher.
    if work_distance_fn is not None:
        new_decisions = refine_work_distance(new_decisions, distance_fn=work_distance_fn,
                                             transit_fn=transit_fn, config=config)

    # Street-name → district geocode (opt-in via geocode_fn): drop postcode-less listings
    # (street only in the title) that geocode to an excluded district (Noord / far-west
    # Nieuw-West / Zuidoost). Runs before the costlier detail-page reads.
    if geocode_fn is not None:
        new_decisions = refine_geo_geocode(new_decisions, postcode_fn=geocode_fn, config=config)

    # Read each surviving listing's detail page to catch dealbreakers the card hides
    # (short-term lease, income cap, no-registration). Opt-in via detail_fetcher.
    if detail_fetcher is not None:
        new_decisions = refine_with_details(new_decisions, fetcher=detail_fetcher, config=config)

    # Tier-3 commute refine (opt-in): a confirmed >10-min walk to Centraal drops the
    # commuter-city listing before it is stored or pinged.
    if commute_runner is not None:
        new_decisions = refine_commute_listings(new_decisions, runner=commute_runner)

    for decision in new_decisions:
        store.record(decision, ts=ts)
        if decision.verdict in (Verdict.SHOW, Verdict.FLAG):
            # Drafting is off by default (the agent surfaces listings only). draft_fn
            # stays injectable; pass draft.draft_intro to attach a draft the user
            # reviews and sends themselves.
            draft = ""
            if draft_fn is not None:
                try:
                    draft = draft_fn(decision.listing)
                except Exception:
                    draft = ""
            notifier.instant(decision, draft)
    return new_decisions

