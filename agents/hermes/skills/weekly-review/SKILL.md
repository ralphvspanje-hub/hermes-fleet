---
name: weekly-review
description: Fires on the Sunday weekly review in the DM: the scheduled message arriving, the user replying to it, or the user asking to run or redo their week ("how did my week go", "let's do the weekly review"). Goal-aware, capture-by-confirm: files their confirmed practice takeaway and pain point in their own words. Not ad-hoc dumps (day-capture) or calendar questions (ops-actions).
metadata:
  hermes:
    tags: [weekly, capture, goals]
---
# Weekly review (Sunday)

Hermes's Sunday rhythm in the main DM: a light, goal-aware look back over the week. Quiet competence,
not chatter. Ground everything in the user's living goals, `goals/north-star` (the stable
destination) and `goals/current` (this period's focus, standing quest, and weekly practice), so the
review ties to their real focus.

## When to Use
When the Sunday weekly review prompt lands in the DM and the user replies, or they ask to run or redo
their week ("how did my week go", "let's do the weekly review"). Ad-hoc dumps outside this flow
(their day, a meeting, a win, pasted content) are owned by `day-capture` (and `win-star` /
`raw-input-distill`); calendar questions by `ops-actions`; logging a miss by `error-log`. Not this
skill.

## Procedure
1. **Ground in goals.** Recall `goals/north-star` and `goals/current` (and the relevant leaf page)
   so the look-back lands specifically and you can gently flag drift. Keep it short.
2. **Weekly practice takeaway.** `goals/current` names one weekly practice. If they share what it
   taught them this week, file it in THEIR words to `lessons/<slug>` (tag `own`, link the goal leaf
   the practice serves).
3. **Pain point** (an example standing quest: collecting unsolved problems; swap in whatever quest
   your `goals/current` names). If they name a real, unsolved problem they or someone around them bumped into,
   file it as a candidate to `problems/<slug>` (tag `own`). If `goals/current` has a standing quest
   that these feed, link it.
4. **Error-log pattern scan (silent, read-only).** While composing the reply, scan this week's
   `logs/error-log` entries. Mention a pattern ONLY if it genuinely repeats (2 or more similar
   entries this week or across recent weeks), one sentence max. No entries or no repeat: say nothing
   about the log. This skill only READS the ledger; writing entries belongs to `error-log`.
5. **Capture by confirm.** File ONLY what the user replies, in THEIR words. "skip" or silence saves
   nothing. The "did I do my practice" status is ephemeral: acknowledge it, don't save it as a page.
   Don't lecture; one gentle nudge at most if they skipped the practice.
6. **Abstract sensitive specifics.** Never store a raw event title or anyone's personal data
   verbatim; store the learning ("align stakeholders before pushing velocity"), not the artifact.
7. **One question max.** If a single question would deepen a kept item, ask it; otherwise let it rest.

## Pitfalls
- The review text is yours and ephemeral: never save it as a page.
- Don't save your own synthesis; only the user's own words become pages (provenance `own`).
- Don't over-build the weekly review: it is deliberately small (one practice + one pain point).
  Deeper monthly or quarterly cadences are intentionally out of scope; don't invent them.
- The error-log scan is silent unless a repeat is real; never a standing question.

## Verification
Replied-to items are filed as `own` with links; ignored or "skip" items save nothing; no raw titles
or personal data stored; practice takeaway to `lessons/<slug>`; pain point to `problems/<slug>`; the
error-log scan stayed read-only and silent unless a real repeat; the review text was never saved as a
page.
