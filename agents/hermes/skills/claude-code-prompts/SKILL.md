---
name: claude-code-prompts
description: "Write copy-ready prompts (briefs) for Claude Code, the user's build agent. Use when the user asks for a prompt for Claude Code/Cursor, wants something built, fixed, or investigated there, or shows a prompt that underperformed and wants it improved."
metadata:
  hermes:
    tags: [prompts, claude-code, build-agent]
---
# Claude Code prompts

A good prompt is a **brief**, what you'd hand a competent contractor: the goal, the context they
can't guess, the constraints, and how you'll both know it's done. Claude Code is highly capable and
reads the target repo itself; the brief's job is direction, not instruction.

## When to Use
When the user asks for a prompt for Claude Code (or Cursor), asks how to phrase a request to their
build agent, or wants a prompt improved after a weak result. Not for prompts aimed at other tools or
people.

## Procedure
1. **Ground it.** Recall what you actually know (the project, `goals/current`, past conversations).
   Name files, paths, or commands ONLY if you know them from the brain or this conversation:
   otherwise write "find where X lives" and let the agent locate it. A wrong path is worse than none.
2. **One question max.** If the goal or scope is genuinely ambiguous, ask one question first;
   otherwise draft.
3. **Draft the brief in four parts**, each a sentence or two:
   - **Goal**: the outcome, not the steps. What is true after, that isn't true now?
   - **Context**: what exists, where it lives, why now. Point at files/docs; never paste what the
     agent can read itself.
   - **Constraints & non-goals**: what must hold, what to leave alone, what NOT to build.
   - **Done-when**: a checkable criterion (tests pass, X visible on screen, doc updated). "Make it
     better" invites the agent to stop early; "the signup test passes and the README documents the new flag" doesn't.
4. **Safety line when it touches live systems:** add "snapshot first; ask before anything
   destructive or outward-facing."
5. **Deliver the brief as one plain-text Telegram message on its own**, nothing before or after it,
   so a long-press copies exactly the brief. Put any assumption you made in a separate message, not
   in the brief bubble. Done when the user can paste it unchanged. Most good briefs are 4-10
   sentences.

## Pitfalls
- Spec-shaped walls of bullets with invented file paths: fabricated detail reads as authority and
  sends the agent to the wrong place.
- Dictating implementation steps. Say what and why; the agent decides how. Only prescribe an
  approach when the user genuinely requires that approach.
- Restating what the target repo's CLAUDE.md already enforces (conventions auto-load there).
- Padding: personas ("act as a senior engineer"), courtesy, "think step by step", all no-ops for
  Claude Code; they cost tokens and add nothing.
- Two tasks in one brief. Sequels become a second prompt ("after that lands, I'll ask for...").
- If the user wants the work QUEUED for the build agent rather than pasted themselves, file it to
  `inbox/requests/<slug>` instead of (or in addition to) a prompt.
- These aren't mutually exclusive: for an ask that needs genuine design thinking (not a fully
  spec'd build) AND the user wants something to paste right now, do both: file the full problem,
  context, and open questions to `inbox/requests/<slug>` (durable, found even if the prompt is never
  pasted), then hand over a short copy-ready prompt that points Claude Code at that slug rather than
  restating everything inline.

## Verification
The delivered brief: one plain-text message on its own bubble; names goal + done-when; every path in
it is known-real; no restated repo conventions; no persona/padding; one task.
