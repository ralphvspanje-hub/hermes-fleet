# Teach conventions: workspace overlay

Follow the canonical `/teach` skill **exactly as written**. These are the **only** two additions, both purely mechanical (output format). They must **not** change any teaching decision the skill makes.

## 1. Copy-results footer (every lesson)
End every lesson with a **"Copy results"** button that copies **one minimal line** to the clipboard, summarizing how the learner did. Include whatever the lesson actually contains:

- **If the lesson has auto-graded MCQs:** include the score: `MCQ <correct>/<total> (<pct>%)`.
- **For each open-ended question:** include the question (short) and the learner's typed answer.
- Omit the MCQ part entirely if the lesson has no MCQs; omit the open-question part if it has none.

Format (assemble from what's present):
`Lesson <N> · <track> · MCQ <correct>/<total> (<pct>%) · "<open q1>": <answer1> · "<open q2>": <answer2>`

The button only writes to the clipboard: **no backend calls**. The learner pastes this line into the track's Telegram topic to get feedback, so keep it minimal (no embedded correct answers; the teacher already has the lesson).

**Must work over plain HTTP:** the hub is served without HTTPS (a bare tailnet address), where `navigator.clipboard` is blocked. So the copy must try `navigator.clipboard.writeText(...)` **and fall back** to a hidden `<textarea>` + `document.execCommand('copy')` when the clipboard API is unavailable.

## 2. Emit the hub link
After writing a lesson, print **exactly one line** so the bot can post the link:

`HUB_URL: <hub-base>/<track>/lessons/<file>.html`

The engine injects `<hub-base>`; you just emit the correct path.
