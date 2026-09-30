---
name: day-capture
description: Fires when the user ad hoc dumps or narrates their day, a meeting, a task they did, a thought, a feeling, or a situation in the DM. Not a reply to the Sunday weekly review (weekly-review owns that); not a pure miss report (error-log owns those); not a clear win (win-star owns those); not pasted external content (raw-input-distill owns that); not a pure website ask (website-queue owns those).
metadata:
  hermes:
    tags: [capture, journaling, reflection]
---
# Day capture: file the dump, then reflect

The user dumps their day here (meetings, tasks, thoughts, feelings, a situation they are chewing on). Catch it into the brain cleanly, then be their mentor about it: a sharp reflection, not a barrage of questions.

## When to Use
When the user narrates or dumps their day, a meeting, tasks they did, a thought, a feeling, or a situation, ad hoc in the chat. NOT a reply to the Sunday weekly review (that is `weekly-review`); NOT a pure miss report (that is `error-log`); NOT a clear accomplishment (that is `win-star`); NOT pasted external content (that is `raw-input-distill`).

## Procedure
1. **Capture first.** File the dump to `journal/<date-or-topic-slug>` the moment it lands, in the user's own words, tagged `own`. Do not wait for answers to any follow-up: the entry is saved even if the conversation stops here.
2. **Pull durable rules out.** If the dump holds a reusable rule or learning, give it its own `lessons/<slug>` page and `[[link]]` it from the journal entry. One dump can yield several captures: split by subject.
3. **Cross-link aggressively.** Wire in `[[people/...]]` and `[[projects/...]]` so the brain connects over time.
4. **Then reflect as Hermes.** One brief, honest reflection, plus AT MOST one sharp, calibrated follow-up, and only when it earns its place. Heavy or searching content (an unexamined assumption, a vague claim to sharpen, a recurring pattern, an unnamed emotion, a goal link) gets one real question. Light logging gets none. Never interrogate: one question or zero.
5. **Enrich on reply.** If the user answers, fold the added depth into the SAME page. Never lose an entry because they did not reply; they can revise anytime ("change that", "actually it was...").
6. **Win, miss, or website ask inside a dump, hand it off.** A clear accomplishment goes through the `win-star` flow (raw win first, then STAR(R) grilling); a miss or mistake gets its short ledger line through the `error-log` flow; a "that should go on my website" ask gets its queue entry through the `website-queue` flow. The journal entry itself stays here either way.

## Pitfalls
- **Work confidentiality.** Store the abstracted learning, never the confidential artifact: no secrets, internal docs/metrics/roadmaps/strategy verbatim, comp numbers, or colleague/customer personal data.
- **Provenance.** Only the user's own words become pages, tagged `own`. Do not save your own synthesis as a brain page; if you framed something well, offer to capture it as their learning in their words.
- Don't delay capture waiting for an answer; file immediately, enrich later.
- Don't stack questions or interrogate: one well-aimed question beats three, and light entries get none.
- Wrong lane: a reply to the Sunday review is `weekly-review`; a pure miss report is `error-log`; pasted external content is `raw-input-distill`; a pure website ask is `website-queue`.

## Verification
The dump is filed to `journal/<date-or-topic-slug>` (plus any `lessons/`), tagged `own` and cross-linked, even if the user never answered a follow-up. You gave one brief reflection and one calibrated question or none, never a barrage. Any win went to `win-star`, any website ask to `website-queue`; no agent synthesis or confidential specifics were saved.
