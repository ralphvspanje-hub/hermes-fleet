---
name: grill-pack
description: Use in a track topic when the user asks to be grilled or drilled by voice - "grill me on lesson 3", "drill me on eigenvectors", "give me a grill pack" - to assemble a short paste-ready payload for their ChatGPT "Grill me" project (voice drill). Also fires when they paste a voice-session debrief back into the topic: probe it, then record_feedback and offer a concept capture.
metadata:
  hermes:
    tags: [teaching, drilling, capture]
---
# Grill-pack: payloads for a "Grill me" ChatGPT project

The user drills themselves out loud in a ChatGPT **Grill me project** (a ChatGPT Project
with voice mode), whose standing instructions hold ALL the drill rules (one question at a
time, withhold answers, re-ask until right, debrief protocol). You don't run the drill and
you don't repeat those rules: you hand them a short **payload** (the what), then metabolise
the **debrief** they bring back.

## When to Use
In a **track topic** (the Channel Topic name is the track slug), when the user asks to be
grilled or drilled by voice, or names a lesson or topic to be grilled on - and again when
they paste a debrief back from a voice session.

## Procedure
Two branches: assemble the payload, or process a debrief.

### Branch A - assemble the payload
1. **Track = the Channel Topic.** Scope everything to that slug (same as `teach-lesson`). No
   Channel Topic → this topic isn't wired up yet; say so, don't guess a track.
2. **Fix the scope.** A named lesson ("lesson 3") → that lesson. A named theme
   ("eigenvectors") → that topic, distilled across the lesson(s) and mission that cover it,
   not one lesson. Nothing named with one obvious latest lesson → use it (`lesson_status`,
   or `list_lessons` to see what exists). Nothing named and it's ambiguous → ask which
   before building; don't silently default. The payload's first line names the scope, so
   the user can catch a wrong pick.
3. **Distill - concepts, not HTML.** Read the raw material once: `read_lesson(track=<Channel
   Topic>, which)` for the 3-6 **key concepts** in scope (the ideas, one plain line each -
   NOT the lesson HTML), the mission one-liner and glossary terms (recall the track's
   mission and glossary from the brain; omit the terms line if there are no glossary
   terms), and any known weak spots from the track's `learning-records` (brain `search`).
   Real material only - omit a section rather than invent a gap or a term.
4. **Fill the template** below: replace every [BRACKET]. Drop a line whose bracket is empty
   (no known gaps → no weak-spots line) rather than sending an empty label.
5. **Keep it one plain bubble.** The filled payload is one Telegram message: **plain prose, no
   code fences, no [brackets], no [[wikilinks]], no `tags:` lists** - those break the bubble.
   3-6 short concept lines keep it comfortably under the **3,500-character** ceiling; never
   split it across bubbles (a split payload can't be copied in one tap).
6. **Send the payload alone.** Your whole reply is the payload - nothing before it, nothing
   after it - so a long-press copy grabs exactly it. The user pastes it into a new chat in
   their Grill me project and taps voice; the project instructions do the rest. Don't
   prepend a how-to: if they ever ask how the loop works, explain in a separate turn, never
   glued to a payload.

**The template** (structure adapted from Matt Pocock's `grilling` skill - MIT, (c) 2026 Matt
Pocock; the drill RULES live in the ChatGPT project, not here). Fill the brackets; send it
WITHOUT these code fences:

```
Drill me on: [TOPIC] (from my [TRACK SLUG] track).
My goal with this: [MISSION ONE-LINER].
What I have studied: [3-6 KEY CONCEPTS, one line each].
Terms I should be able to use correctly: [GLOSSARY TERMS].
Watch for these known weak spots: [GAPS/MISCONCEPTIONS, if any].
```

### Branch B - process the debrief
The debrief is **the voice model's claims about the user, not evidence.** Learning-records
stay evidence-gated.
1. **Ground first.** `read_lesson(track=<Channel Topic>, which)` so you discuss the real
   content, never a memory of it.
2. **Probe before you trust.** Take 1-2 debrief lines - one "nailed", one "gap" - and make
   the user show it in chat (explain it, apply it). Their answer, not the debrief's
   assertion, is the evidence.
3. **Record.** `record_feedback(track=<Channel Topic>, results)` with a short results summary
   built from the debrief plus what they just showed you - so the engine updates
   `learning-records/` on what they actually know.
4. **Offer the concept capture.** Run teach-lesson's concept-capture step (load it with
   `skill_view("teach-lesson")` if its body is not already in this session): dedup by
   `search` → compose `concepts/<slug>` → clean prose preview → one "yes / tweak / skip".
   Compose the page from what **the user showed you in chat, in their own words** - never
   from the debrief text, which is a claim, not knowledge. One offer; capture only on an
   explicit yes.

## Pitfalls
- **Never put drill rules back into the payload.** The how lives in the ChatGPT project's
  standing instructions, configured outside this system; duplicating it bloats the voice
  context and the two copies drift. The payload is facts only: topic, goal, concepts, terms,
  weak spots.
- **Rendering:** the sent payload is one plain bubble - see Branch A step 5. Never split it.
- **Concepts, not the lesson HTML.** Voice context is short; a compact payload drills harder.
  If a session "forgot" the brief, the fix is a shorter payload, not a longer one.
- **Never recite a lesson from memory** - `read_lesson` first, in both branches (same rule as
  `teach-lesson`).
- **Debrief ≠ proof.** Probe at least one claim before `record_feedback`; the drill counts as
  evidence only through the user, not through the debrief's summary.

## Verification
Track came from the Channel Topic; the chosen scope shows in the payload's first line; the
payload went out as one plain-prose bubble (facts only, no drill rules, well under 3,500 chars)
as the whole reply; on a debrief you probed ≥1 claim before `record_feedback` and made exactly
one concept-capture offer sourced from the user's own words.
