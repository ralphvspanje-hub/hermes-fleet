---
name: win-star
description: Fires when the user reports an accomplishment or something that clearly went well anywhere in the Hermes DM: a launch shipped, praise received, a hard problem cracked, a goal hit, a proud work or life moment. Not a Sunday weekly-review reply (weekly-review) or a miss report (error-log), and distinct from day-capture: a win report fires here; when a general day dump contains a win, day-capture hands it here.
metadata:
  hermes:
    tags: [capture, wins, career]
---
# Win to STAR(R) capture

The user reports something that went well; you turn it into a durable, interview- and promotion-ready record. File first, grill after.

## When to Use
When the user reports a win or accomplishment anywhere in the DM: a launch, positive feedback, a hard problem solved, a goal hit, a proud moment at work or in life. If a broader day dump contains a win, day-capture files the day and hands the win here.

## Procedure
1. **File the raw win immediately.** The moment the user reports it, write it to `wins/<slug>` **as sent**, tagged `own`, before any grilling. This guarantees the win is captured even if the conversation stops right here.
2. **Grill it into STAR(R), one question per turn** (never several at once), conversational, folding each answer back into the *same* page as it arrives:
   - **Situation / Task**: what was at stake, what was your responsibility?
   - **Action**: what did *you* specifically do (not "the team")?
   - **Result**: the outcome, quantified wherever possible.
   - **Reflection**: what it shows about you, what you'd repeat.
   Any element they never answer stays on the page as an open question, not dropped.
3. **Cross-link** the same page with `[[ ]]` to the `[[people/...]]` and `[[projects/...]]` involved.
4. **Confidentiality carve-out**: store the abstracted win, never confidential specifics (no internal metrics verbatim, comp numbers, or colleague/customer personal data).

## Pitfalls
- A vague win is useless: get at least one concrete number or fact.
- Don't ask all five at once; one question per turn.
- Don't fabricate detail; capture only what the user confirms, in their words. Never save your own synthesis as the page.
- Not the Sunday review reply (that is `weekly-review`) or a miss report (that is `error-log`).

## Verification
The `wins/<slug>` page exists even if the user stopped answering after their first message, with any STAR(R) elements they never gave marked as open questions on the page. Once the grilling completes, the page carries all five STAR(R) elements, at least one quantified result, provenance `own`, and `[[ ]]` links to the relevant people and projects.
