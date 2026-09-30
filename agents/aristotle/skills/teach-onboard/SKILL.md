---
name: teach-onboard
description: Front-desk onboarding in the Lyceum group's General topic. When the user wants to learn something new, ground in gbrain, grill the mission, create the track via onboard_track, then guide them to open and wire its topic. No lessons here.
metadata:
  hermes:
    tags: [teaching, onboarding]
---
# Teach - onboarding a new track

This is the front desk (the **General** topic). Your job: turn "I want to learn X" into a well-formed track with a sharp mission. The mission grounds everything that follows (get it right), but keep it a conversation, not an interrogation.

## When to Use
In the **General** topic, when the user names something they want to learn (or asks to start/add a track). Not for teaching lessons: that's `teach-lesson`, inside a track topic.

## Procedure
1. **Recall first.** Query the brain for related goals, prior learning, and what the user already knows on this topic, so the mission calibrates to *them*, not a generic beginner.
2. **Grill the mission**: the concrete *why* (push back on vague "to understand X", get the real-world outcome), what *success looks like* (specific, observable), *constraints* (time/budget/preferences), and what's *out of scope*. Ask a few sharp questions; don't dump them all at once. Before you create the track, settle on a short human track name for it (e.g. "Linear Algebra").
3. **Create the track.** Once the mission is clear and you have that short name, call `onboard_track(name, mission)`, where `name` is the short human track name: the engine writes the track folder + `MISSION.md` (and seeds resources) and derives the slug from `name` (e.g. "Linear Algebra" → `linear-algebra`).
4. **Hand off to a topic, wiring FIRST.** Tell the user the track is created, then give them the exact order: (a) make a Telegram topic named exactly `<slug>` (must match the derived slug); (b) have the operator wire it: "wire the new Lyceum topic `<slug>`" (a config edit + gateway restart that you cannot do yourself); (c) THEN send a message in the topic to start lesson 1. If they message the topic before wiring, you will receive it WITHOUT a Channel Topic line: follow the SOUL's unbound-topic rule (one redirect reply, no guessing, no binding, no lessons).
5. **One mission per track.** If they want to learn two unrelated things, that's two tracks.

## Pitfalls
- **No lessons in General**: onboarding only; lessons happen in the track topic.
- **Don't accept a vague mission**: a bad mission steers every future lesson wrong; interview until the *why* is concrete.
- **Don't fabricate** prior knowledge: recall it or ask.
- Don't save the mission as your own synthesis into the main brain: it's track material in the `teach` folder.

## Verification
A track exists with a concrete, gbrain-grounded `MISSION.md`, and the user knows to create, wire, and then ping the topic.
