# Lessons learned

Things that cost time while running the fleet, each with the reason behind it. Versions
change and some of these may be fixed upstream by the time you read this; check before
you rely on them.

## Telegram

- **Keep `rich_messages: false`.** With rich messages on, a long plain-prose reply is
  streamed up to a large internal cap, then finalized through a Telegram edit whose real
  limit is 4096 characters. The reply is cut off silently, with no error in the logs.
  With it off, long replies split into numbered messages and nothing is lost. The cost
  is that tables and math render as plain text. Set it in every profile, including new
  ones.
- **Keep code fences, `---` front matter, `[[wikilinks]]` and `tags:` lists out of chat
  bubbles.** The plain Markdown parser rejects some of them, and then the whole bubble
  falls back to raw unformatted text. Tell each agent (in its SOUL) to write readable
  prose in chat and put structured content into the brain instead.
- **Skills load on a new session.** After installing or changing a skill, send `/new` in
  that chat or topic. Otherwise the old session keeps running without it and you will
  think the skill is broken.

## Skills and personas

- **An agent's claims must match its tools.** If the SOUL says the agent can do
  something its tools do not deliver, it does not say "I can't"; it fabricates to fill
  the gap. The reverse also bites: a SOUL that says "you cannot set reminders" makes it
  refuse a tool it actually has. Keep the abilities line in each SOUL in sync with the
  real toolset, and add a rule to say "I can't see or do that" before giving any
  judgement.
- **Images are only attached on the turn they arrive.** On a follow-up turn the agent
  sees a file path, not the picture. Give it a re-inspect tool (`vision_analyze`) and a
  rule never to bluff perception.
- **Agents that can edit their own skills will drift from your repo copy.** Hermes can
  patch skill files from chat. Before you deploy a skill from your repo, diff it against
  the server copy, or you overwrite something the agent was asked to remember.
- **Pin the settings you rely on.** An upstream release once changed the default
  approval mode to an LLM-judged one. Configs that set `approvals.mode: manual`
  explicitly were unaffected. Pin anything security-relevant rather than trusting the
  default.
- **Retire what does not earn its place.** Daily morning briefs and evening digests were
  built, then switched off because they were noise; the one weekly check-in stayed. Ship
  a minimal version first, and add the next layer only once the small one proves itself.

## Web tools and paid APIs

- **Web tool backends are picked by key presence.** Hermes chooses the search and
  extract backend by which API key is present in the profile's `.env`, not by which one
  is healthy. When web tools misbehave, check the `.env` first, not just `config.yaml`.
- **Search credit budgets are shared.** Every gateway using the same search API key
  draws from one monthly credit pool. Errors near the end of the month are probably the
  quota, and there is no automatic fallback to another backend while the key exists.
- **Scraper APIs can bill per item scraped, not per result returned.** One actor
  scraped thousands of items internally to return a few dozen, and each run cost far
  more than expected. Scrape occasionally into a local cache and serve requests from the
  cache; never scrape per chat request.
- **Missing packages hard-fail on purpose.** With lazy installs off, an optional
  dependency that is not installed makes the feature fail until you install it. That is
  the price of nothing installing itself.

## gbrain and embeddings

- **Embed in small batches with sleeps.** Query embedding and bulk imports share the
  same provider rate limit. A big import once exhausted a free-tier quota, live queries
  started returning empty results, and the agents fell back to guessing. Even on a paid
  tier, embed in batches of about 15 with a pause of about a minute between them, and
  avoid big imports while the agents are in use.
- **Reindex an edited page with `put`, not a bulk `import`.** A bare `import` of a
  directory can resolve to the wrong source and create junk pages. `put` on the one page
  is precise.
- **Tag reconcile on `put` is additive.** A tag removed from the file stays on the page
  in the database; remove it explicitly with `untag`. `put` also writes the merged page
  back to disk, overwriting your edited file, so check the result with `get`.
- **Some model settings live in the config file, not the database.** Check which plane
  a gbrain setting lives on before assuming a `config set` took effect, and verify with
  the page's embedding signature.
- **Use dated model ids for capped LLM runs.** gbrain's price table is keyed by dated
  model snapshots. A dateless id has no price, and cost-capped runs refuse to start.
- **Export every key in env files you source.** A key line without `export` sets a
  shell variable the child process never sees. A nightly job silently skipped its LLM
  phase for weeks because of this.
- **Use Postgres for more than one agent.** Several agents each running their own
  gbrain MCP process against one embedded database directory can corrupt it.
- **One long page recalls badly.** A single big goals page embeds as a few diluted
  chunks and rarely surfaces. A short hub page linking to one focused page per goal
  ranks like any other concept page.

## Long jobs

- **Run anything slow asynchronously.** A lesson takes several minutes of model time.
  A synchronous tool call was killed by MCP keepalive reconnects long before it
  finished. Spawn the job detached, return at once, write status to a file, and have the
  job post its own result to the chat.
- **Guard against double spawns.** A retried "next lesson" can start a second
  expensive run. Take an atomic lock file before spawning and hold a lock for the whole
  job.

## Operations

- **Upgrade deliberately.** Snapshot first, read the release notes, pin to a release
  commit rather than the tip of the main branch, and re-verify each agent afterwards.
  Watch for install hooks that run migrations on their own.
- **Restart the gateway after a config change**, then `/new` so the session picks it up.
