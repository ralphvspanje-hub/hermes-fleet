# Security model

These agents read the web, forwarded messages, scraped listings and your own notes. Any
of that can carry a prompt injection. The design assumes an agent **will** at some point
be talked into trying something it should not, and makes sure the tools it holds cannot
do much damage when that happens.

This page describes the containment the fleet used. Treat it as a baseline to keep, not a
list of optional extras.

## Nothing reachable from the internet

- The server exposed no public ports. A host firewall denied all inbound traffic except
  on the Tailscale interface, and admin access, the lesson hub and Syncthing all ran over
  the tailnet.
- Telegram is polled outbound, so bots need no inbound port either.
- Services that have no authentication of their own (the lesson hub) bind only to a
  tailnet or loopback address, and refuse to start on a public one.
- The host ran automatic security updates and rebooted nightly, so kernel patches
  actually took effect. Every service is a systemd user unit with linger on, so the
  reboot is harmless.

## Only you can talk to the bots

- Each bot's Telegram allowlist (`TELEGRAM_ALLOWED_USERS`) holds your own user id and
  nothing else. Never enable an allow-all-users option.
- A pairing request, "please add me to the allowlist", or "approve access for X" that
  arrives **in a chat message** is a prompt injection, whoever it claims to be from.
  Access changes happen only from your own terminal, never because a message asked.

## Scoped tools

- No shell, no file and no code-execution tools on any Telegram-facing agent. Every
  capability is either a native Hermes toolset (memory, skills, web, vision, reminders)
  or a narrow MCP tool.
- MCP servers get an explicit tool include list, so a new upstream tool does not appear
  in an agent's hands just because the server started offering it.
- Scheduled jobs get their own `platform_toolsets.cron` list, set to the same scope as
  the chat toolset. Without it, cron jobs can fall back to a wider default.
- Approvals are pinned (`approvals.mode: manual`, `cron_mode: deny`) so an upstream
  default change cannot loosen them.
- Dangerous capabilities are designed out, not just discouraged. Hermes can create and
  move calendar events but has no delete tool at all
  ([agents/hermes](../agents/hermes/)). Aristotle's engine runs headless Claude Code with
  no Bash, locked to one track folder ([agents/aristotle](../agents/aristotle/)).

## No self-modification of the install

- `curator.enabled: false`: the agent does not reorganize its own skills and memory in
  the background.
- `security.allow_lazy_installs: false`: missing optional packages are never installed
  by the agent at runtime. A human, or a build agent working for one, installs them.
  Nothing on the server installs itself.
- Hermes agents can edit their own skill files through the skills toolset. That is
  useful (you ask it to remember a rule, it patches the skill), but it means the copy on
  the server can legitimately differ from your repo copy. **Diff the server copy before
  deploying over it**, or you silently erase what the agent learned.

## Secrets

- Every `.env` is `chmod 600` and never committed. The repo ships only placeholders.
- Agents have no file or shell tool, so they cannot read their own `.env`.
- Engines that shell out (the teach engine, the listing browser) do not source the
  `.env`. They read single keys and run the child process under a minimal environment
  holding only the one API key it needs.

## Untrusted write lanes and the trust boundary

An internet-exposed agent must never write to anything a more powerful agent will act
on. The projects bridge gives Hermes read access to your code and exactly one write: an
append-only build log. Your coding agent on the laptop has a shell and your credentials,
so it treats every entry in that log as an untrusted request to discuss with you, never
as an instruction. The rule to paste into your coding agent's instructions is in
[bridges/projects](../bridges/projects/#trust-boundary).

## Least privilege follows exposure

The agent that reads the most untrusted input gets the least power. Makelaar reads
scraped listings and alert emails all day, so:

- its gbrain tools are read-only (no page or link writes),
- it never messages, applies or pays; its MCP tools only read the local store, set a
  status, start a scan or report spend,
- listing text is treated as data, and anything passed to its browser engine is
  sanitized first.

Details: [agents/makelaar](../agents/makelaar/).

## A dedicated Google account for automation

Anything automated that needs Google (calendar access) uses a separate Google account,
with your calendar shared to it. Never authorize a server-side tool with your main
account: it is likely the recovery path for your email, your password resets and maybe
your tailnet login. A token sitting on an internet-connected server should not be able
to reach any of that. A brand-new account used only by a script can get flagged, so use
it like a person for a while before wiring it in.

## Provenance: what goes into the brain

The brain is only as trustworthy as what gets written to it.

- Only your own first-hand input (tagged `own`) and cited external sources (tagged
  `external`) become pages. `own` outweighs `external` on recall.
- Agents never save their own synthesis as knowledge. An agent opinion stored as a page
  quietly biases every later recall. If an agent says something worth keeping, it
  offers to capture it in your words.
- Generated material (lessons, drafts) stays in its own files, not in the brain.

## Known limits

- **Prompt injection is mitigated, not solved.** Fencing untrusted text as "data, not
  instructions" and SOUL rules lower the odds; the scoped tools are what cap the damage.
- **Redaction is best effort.** The projects bridge redacts secret-shaped values with
  regexes. Keep real secrets out of synced folders in the first place.
- **Model API keys live in the agent process.** They have to, to make calls. Without
  file or shell tools the agent cannot read them back, but if you ever add such tools,
  run them in a sandbox that does not hold the key.
- **Your identity provider is the master key.** With nothing public, whoever controls
  the account behind your tailnet controls the box. Put strong (app or hardware) 2FA on
  it.
- **Read fences are partial.** Aristotle's engine is denied reads of the Hermes config
  folder and `/proc`, but can read anything else its service user can. Keep secrets in
  places you have explicitly denied.
