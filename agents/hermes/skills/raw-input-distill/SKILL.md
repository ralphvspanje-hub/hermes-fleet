---
name: raw-input-distill
description: Fires when the user pastes or forwards external material (an article, a podcast or talk's takeaways, a quote, a book passage, live notes while listening), asks to save something they read, watched, or heard, or asks to keep a full article/text ("save the whole article"). External content to distill (and optionally keep verbatim in the library drawer), distinct from capturing their own day (day-capture), a miss report (error-log), and the Sunday weekly review (weekly-review).
metadata:
  hermes:
    tags: [external, capture, distill, library]
---
# Raw input: distilled external note

## When to Use
When the user pastes or forwards external content (article, podcast, talk, quote, book passage, live
listening notes), asks to save something they read, watched, or heard, or explicitly asks to keep the
full text ("save the whole article"). Not their own day (that is `day-capture`) or a miss for the
error log (that is `error-log`).

## Procedure
1. **Read it, then distill.** Pull the durable takeaway(s), the idea worth keeping, not the whole text.
2. **File the takeaway** to `concepts/<slug>` (the idea or framework) and/or `sources/<slug>` (the
   source itself). Tag `external`. Name the source in-text ("Source: <podcast>, episode on pricing").
3. **Capture the user's OWN reaction separately.** If they add their own take, lesson, or how it
   applies, save THAT in their words, tagged `own` (a `lessons/<slug>` if it is a durable rule), not
   blended into the external page. External input is not their own lesson until they have lived it.
4. **Full-text keep (ONLY on an explicit ask).** If the user says to save the whole article or text:
   get the complete text (`web_extract` on the URL, or their pasted text) and save it VERBATIM with
   the library lane's `put_page` (the `gbrain_library` tools, a separate drawer) as `sources/<slug>`
   (frontmatter `type: source`, tag `external`, URL named in-text). The library drawer keeps bulky
   verbatim text out of the main brain's recall ranking; it is chunked, embedded, and searchable
   there (via the `gbrain_library` `search`) whenever the user asks to check the library. Still do
   steps 1-3: the distilled brain pages are the recall lane, the library copy is the reference. On
   the BRAIN's `sources/<slug>` page (step 2), add one line: "Full text kept in the library as
   sources/<slug>", so when a brain page surfaces later you know the original is one
   `gbrain_library` get_page away. Confirm both in one line ("distilled to concepts/x + full text in
   the library as sources/y"). If `web_extract` returns a truncated page, say so honestly and save
   what was actually retrieved, marked as partial.
5. **Cross-link** `[[concepts/...]]`, `[[lessons/...]]`, `[[people/...]]`, `[[projects/...]]` so it
   wires in.
6. **Confirm the filing in one line** so the user can correct the slug or the tag.

## Pitfalls
- Keep `own` vs `external` clean: their reaction and the source's claim never share a tag or a page.
- Distill and file, do not write an essay. The page is the idea, not a transcript.
- Full verbatim text NEVER goes into the main brain drawer (it pollutes recall ranking): it goes to
  the library drawer via the `gbrain_library` tools, and only on an explicit ask. Whole books or bulk
  corpus imports are the build agent's job (embedding batch limits, copyright); a single article is
  yours.
- Don't save your own synthesis as a page. The saved content is the source's idea (`external`) or the
  user's own words (`own`), never your commentary.

## Verification
A concise `concepts/` or `sources/` page exists in the brain, tagged `external`, source named in-text,
cross-linked; any reaction from the user is saved separately in their words tagged `own`; on an
explicit full-text ask, the verbatim copy sits in the LIBRARY drawer (never the brain) as
`sources/<slug>` and both were confirmed in one line; no verbatim full-text dump lands in a
main-brain page.
