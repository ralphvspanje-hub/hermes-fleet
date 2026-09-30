---
name: error-log
description: Fires when the user reports a personal miss or mistake ("log this error", "that went wrong", "I messed up", "add that to my error log"), or when day-capture hands over a miss found inside a broader dump. Their running miss-ledger, a sibling of win-star.
metadata:
  hermes:
    tags: [capture, error-log, ledger]
---
# Error log

The user's running miss-ledger: one line per personal miss, in THEIR words, on the ONE brain page
`logs/error-log`. A miss report is an ad-hoc dump type, a sibling of `win-star`.

## When to Use
When the user reports a personal miss or mistake ("log this error", "that went wrong", "I messed up",
"add that to my error log"), or when `day-capture` hands over a miss found inside a broader dump. Rich
reflection on the miss is still `day-capture`'s; this skill only appends the ledger line.

## Procedure
1. **Append, in their words.** Add a 1-2 line entry to `logs/error-log`:
   `**date - situation - what I'd do differently**`, dated from the conversation's current date (never
   from memory). Their words, no agent synthesis.
2. **Append-only mechanics.** `get_page` `logs/error-log` FIRST, add the entry, re-`put` the FULL page.
   A partial put erases the ledger. It stays ONE page: never a page-per-entry scheme or a separate ledger.
3. **Durable rule -> also a lesson.** If the miss yields a durable rule, ALSO create `lessons/<slug>`
   and `[[link]]` it from the short ledger entry (keep the ledger line short).
4. **Route check.** The ledger holds the user's OWN misses. A friction they observed in the world (a
   product gap, an unsolved pain, nobody's fault) is NOT an error: file it to `problems/<slug>` (tag
   `own`). If one event is genuinely both (their miss AND a world friction), ledger line + `problems/`
   page, `[[linked]]`.

## Pitfalls
- Ledger, not a journal: 1-2 lines per miss; rich reflection goes to a `day-capture` journal entry.
- Their words only, no agent synthesis.
- Never a page-per-entry scheme or a separate ledger; one `logs/error-log` page.
- Never re-`put` a partial page (it wipes the ledger); fetch the FULL page first.
- The weekly pattern scan over this ledger is owned by the `weekly-review` skill, not this one.

## Verification
Entry appended to `logs/error-log` in their words (page fetched first, FULL content re-put), dated from
the conversation, ledger never overwritten; a durable rule also captured to `lessons/<slug>` and linked;
a world friction routed to `problems/<slug>` instead.
