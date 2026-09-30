---
name: website-queue
description: Fires when the user says something belongs on (or should change on) their personal website ("add this to my website", "put this on my site", "remove X from my website"), when day-capture hands over a website ask found inside a broader dump, or when the user asks what is queued. Appends to the inbox/website-queue ledger for the build agent. Not for actually editing the site (impossible from here) and not a Hermes feature request (that is inbox/requests).
metadata:
  hermes:
    tags: [capture, website, queue]
---
# Website queue

The user's running list of things they want added to or changed on their personal website. ONE
brain page, `inbox/website-queue`, append-only, a sibling of the `logs/error-log` ledger. You only
keep the queue: the build agent sweeps this page when the user asks it to update the website,
drafts, and publishes after the user approves there.

## When to Use
When the user says something should go on, change on, or come off their website: "add this to my
website", "put this on my site", "remove X from my website". Also when `day-capture` hands over a
website ask found inside a broader dump, and on "what's on the website queue". NOT for editing the
site (you cannot; never imply you did). NOT a Hermes feature or config request (that lane is
`inbox/requests/`).

## Procedure
1. **Append, in their words.** `get_page` `inbox/website-queue` FIRST, add a dated 1-2 line entry
   under `## Open` (`**YYYY-MM-DD** - what they want added/changed/removed, plus any detail they
   gave`; date from the conversation, never from memory), then re-`put` the FULL page. A partial put
   erases the queue. If the page does not exist yet, create it: one intro line ("Things the user
   wants added to or changed on their website; append-only") plus `## Open` and `## Done` sections,
   then append.
2. **Capture the substance too.** If the item leans on a story or fact not yet in the brain, capture
   that through the normal lanes (`day-capture`, `win-star`) and link it from the queue entry: the
   build agent can only publish what the brain holds or the user retells.
3. **Confirm in one line**, naming the gate: it goes live only after the user asks the build agent to
   update the website and approves the draft there.
4. **Read-back.** On "what's on the website queue", `get_page` and summarize the Open entries in
   plain chat formatting.
5. **Done-marking is not yours.** The build agent moves entries to `## Done` with the publish date.
   Never delete or rewrite existing entries; append only.

## Pitfalls
- The site is PUBLIC, and the brain stores no confidential artifacts. If an ask leans on something
  confidential or private (employer specifics, other people's names, money numbers, addresses),
  queue the ask with that detail abstracted or dropped, never verbatim, add a plain-text flag to the
  entry ("check: private?"), and tell the user the detail stays out: the build agent settles exact
  wording with them at publish time.
- Queueing is not publishing: never claim or imply the site was updated.
- Never re-`put` a partial page (it wipes the queue); fetch the full page first.
- Wrong lane: a Hermes feature, fix, or config ask is `inbox/requests/`, not this queue.

## Verification
Entry appended under Open (full page re-put), dated from the conversation, in the user's words; any
supporting story captured through its own lane and linked; one-line confirm sent naming the
build-agent gate; no claim the site changed; existing entries untouched.
