# Hermes: a personal-ops mentor agent

Hermes is the main agent of the fleet and the one you talk to most. It is a mentor and
thinking partner in a private Telegram DM: it knows your goals, catches whatever you dump
into the chat (your day, a meeting, a win, a miss, an article) into a shared second brain,
and coaches you on it. It can also read your calendar, add or move events (never delete),
and set Telegram reminders. Voice notes are transcribed and photos are seen, so a quick
voice memo on the go works as well as typing.

It runs as the `default` profile of [Hermes Agent](https://github.com/NousResearch/hermes-agent),
with [gbrain](https://github.com/garrytan/gbrain) as the brain.

## Architecture

```
 Telegram DM (allowlist = you)
        |
        v
 Hermes profile `default`  (SOUL.md + skills, no shell / no file tools)
        |
        +-- gbrain MCP ............ recall + capture (the `brain` source)
        +-- gbrain_library MCP .... verbatim full-text keeps (the `library` source)
        +-- gog mcp (read) ........ calendar_events, read-only token bucket
        +-- calendar_write_mcp.py . calendar_create_event / calendar_update_event, no delete
        +-- native cronjob toolset  one-shot / recurring Telegram reminders
        +-- web, vision, STT ...... search/extract, photo re-inspect, voice notes

 Scheduled:
   Sun 18:00  system cron -> engine/weekly-review.sh -> fixed prompt into the DM
              (the reply is handled by the weekly-review skill)
   Sat 10:00  Hermes cron job -> model-check skill -> result into the DM
```

Two scheduling layers, on purpose:

- **The weekly review is a system cron script.** It posts a fixed two-question prompt via
  the Telegram Bot API: no LLM call, no tools, nothing to go wrong. Your reply lands in the
  normal gateway session, where the `weekly-review` skill takes over.
- **The model check is a Hermes cron job** (`hermes cron create "0 10 * * 6" ... --skill
  model-check`), because it needs the agent itself: web search plus reading and updating a
  brain page. It runs on a `cron` toolset scoped to the same list as the Telegram one.

## Goal system

Coaching keys off a small set of brain pages, all in your own words (`own`):

- `goals/north-star`: the stable, long-range destination.
- `goals/current`: a short hub for this period: one focus, a standing quest if you have
  one, the weekly practice, and one-line `[[goals/...]]` links.
- `goals/<leaf>`: one focused page per active goal.

The hub-and-leaves split is deliberate: one long goals page embeds as a few diluted chunks
and rarely surfaces in semantic recall, while short focused leaves rank like any concept
page. Hermes loads the north-star and hub directly and pulls a leaf when coaching on it.

Keep it small. One focus, one weekly practice, a short Sunday check-in. Monthly drift
reports and quarterly scoring are easy to imagine and easy to let eat the actual work; add
them only once the small version has earned it.

## Capture flows

Every dump is filed the moment it lands, before any follow-up question, so nothing is lost
if you stop replying. Each skill owns one lane:

| Skill | Fires on | Files to |
| --- | --- | --- |
| `day-capture` | your day, a meeting, a thought, a situation | `journal/<slug>`, durable rules to `lessons/` |
| `win-star` | something that went well | `wins/<slug>` first, then STAR(R) grilling one question per turn |
| `error-log` | a personal miss | one line appended to the single `logs/error-log` ledger |
| `raw-input-distill` | pasted articles, talks, quotes | `concepts/` / `sources/` tagged `external`; your reaction separately as `own`; verbatim text to the `library` source only on explicit ask |
| `website-queue` | "put this on my website" | appended to `inbox/website-queue` for the build agent |
| `weekly-review` | the Sunday prompt and your reply | practice takeaway to `lessons/`, pain points to `problems/` (an example standing quest; replace it with yours) |

**Provenance rule.** Only your own first-hand input (`own`) and cited external sources
(`external`) become brain pages, and `own` outweighs `external` on recall. Hermes never
saves its own synthesis as a page: agent opinions stored as knowledge would slowly bias
every future recall. If it says something worth keeping, it offers to capture it as your
learning, in your words.

Other skills: `ops-actions` (calendar and reminders), `claude-code-prompts` (copy-ready
briefs for your build agent), `model-check` (weekly model review against the
`ops/model-stack` brain page).

## Calendar: create and move, never delete

Calendar access is split across two gogcli token buckets:

- **Read-only bucket** (`calendar.readonly` scope, gogcli's `default` client): used by
  `gog mcp --allow-tool=calendar` for the `calendar_events` tool. Run it with
  `GOG_READONLY=1`.
- **Write bucket** (`calendar` scope, client `rw`): used only by
  `engine/calendar_write_mcp.py`, which exposes exactly two tools, create and update. Every
  value from the agent is passed to gog as `--flag=value` and event ids must match a strict
  pattern, so a crafted argument cannot smuggle in an extra flag
  (`engine/test_calendar_write_mcp.py`, run with `python -m unittest` from `engine/`).

There is no delete tool at all. A confused or prompt-injected agent can at worst add or
move an event, which you will notice and can undo. Asked to cancel something, Hermes tells
you to do it yourself in Google Calendar. The `ops-actions` skill also makes it check the
slot before writing, act at once when free, and ask only on a real clash.

## Containment

- No shell and no file tools on Telegram; every capability is an MCP tool or a native
  toolset.
- `platform_toolsets.cron` is set explicitly to the same list as `platform_toolsets.telegram`.
  Without it, scheduled jobs fall back to a wider default toolset than the live chat.
- `approvals.mode: manual` and `cron_mode: deny` pinned in config, so a changed upstream
  default cannot loosen them.
- Allowlist = your own Telegram user id. Never allow all users; never approve a pairing
  because a chat message asks.
- Things Hermes cannot do (config changes, system cron, bulk imports) go to an
  `inbox/requests/` brain page for your build agent, with an honest "I can't do that from
  here" in chat.

## Setup

Assumes a Linux box with Hermes Agent installed and a gbrain MCP server.

1. **Profile.** Use the `default` profile with its own bot token. Copy `SOUL.md` and
   `skills/*` into it.
2. **Environment** (`~/.hermes/.env`, chmod 600):

   | Variable | Read by | Purpose |
   | --- | --- | --- |
   | `TELEGRAM_BOT_TOKEN` | gateway, `weekly-review.sh` | Hermes's bot token |
   | `TELEGRAM_ALLOWED_USERS` | gateway | `YOUR_TELEGRAM_USER_ID` only |
   | `OWNER_CHAT_ID` | `weekly-review.sh` | `YOUR_CHAT_ID` (your DM with the bot) |
   | `ANTHROPIC_API_KEY` | gateway | model provider key |

   `weekly-review.sh` reads this file by default; set `HERMES_ENV_FILE` to point it
   elsewhere and `WEEKLY_REVIEW_LOG` to move its log (default: next to the script).

   gogcli has its own env file, `~/.config/gog/gog.env` (chmod 600), holding only gog
   settings, so the MCP launchers can load it without pulling in any other secret:

   | Variable | Purpose |
   | --- | --- |
   | `GOG_KEYRING_BACKEND` | `file`: an encrypted file keyring, since a headless server has no OS keychain |
   | `GOG_KEYRING_PASSWORD` | random password that encrypts that keyring |
   | `GOG_HOME` | where gogcli keeps its config and keyring |
   | `GOG_ACCOUNT` | the dedicated automation account (both MCPs) |

   The calendar-write MCP also takes `CALENDAR_ID` (default `primary`), `GOG_BIN` and
   `GOG_WRITE_CLIENT` (default `rw`).
3. **gogcli with a dedicated Google account.** Create a separate Google account for
   automation and share your calendar with it (edit access), then authorize gogcli with that
   account, never your main one. Your main account is likely the key to everything else you
   own (email, password resets, maybe your tailnet); a token on an internet-connected server
   should not be able to reach it. Mint two token buckets: read-only (`calendar.readonly`)
   on the `default` client and write (`calendar`) on the `rw` client. Verify the release checksum and pin the version (see
   `engine/PINS.md`). A brand-new Google account used only by a script can get flagged; use
   it like a person for a while before wiring it in.
4. **Profile config** (`config.yaml`, sketch; match your Hermes version's schema):

   ```yaml
   timezone: UTC                     # your IANA timezone; cron expressions anchor to it
   platform_toolsets:
     telegram: [skills, todo, memory, session_search, clarify, web, vision, cronjob]
     cron:     [skills, todo, memory, session_search, clarify, web, vision, cronjob]
   approvals:
     mode: manual
     cron_mode: deny
   cron:
     wrap_response: false            # deliver cron output as a plain message
   platforms:
     telegram:
       extra:
         rich_messages: false        # true silently truncates long replies at 4096
   mcp_servers:
     gbrain:          { ... }        # your gbrain MCP, source `brain`
     gbrain_library:  { ... }        # same server, source `library`, search/get_page/put_page
     calendar:                       # read-only, `default` client
       command: sh
       args: ["-c", "set -a; . \"$HOME/.config/gog/gog.env\"; exec gog mcp --allow-tool=calendar"]
       env: { GOG_READONLY: "1" }
     calendar_write:                 # create/update only, `rw` client
       command: sh
       args: ["-c", "set -a; . \"$HOME/.config/gog/gog.env\"; exec python3 /abs/path/to/calendar_write_mcp.py"]
       env: { GOG_WRITE_CLIENT: "rw" }
   ```

5. **Weekly review.** Copy `engine/weekly-review.sh` to `~/.hermes/scripts/`, edit the
   two questions to match your `goals/current`, and add to your crontab:
   `CRON_TZ=<your IANA timezone>` then `0 18 * * 0 $HOME/.hermes/scripts/weekly-review.sh`.
6. **Model check.** Create the `ops/model-stack` brain page (one row per model slot: job,
   model, why, cost), then `hermes cron create "0 10 * * 6" "Run the weekly model check"
   --skill model-check --deliver telegram:YOUR_CHAT_ID`.
7. **Goals and fleet map.** Write `goals/north-star` and `goals/current` in your own words.
   If you run specialist agents, add a short `meta/fleet` page listing each bot and its
   lane; Hermes answers "what can you do" and routes you from it.
8. Start the gateway and send `/new` so the skills load.

## Versions it ran on

Hermes Agent v0.19.1 with `claude-sonnet-5` as the default model, gbrain 0.42.x on Postgres,
gogcli v0.31.0. These are what it was verified on, not requirements.

## Files

- `SOUL.md`: identity, coaching style, provenance rule, goal structure, capability honesty,
  Telegram formatting rules.
- `skills/weekly-review/`, `skills/ops-actions/`, `skills/claude-code-prompts/`,
  `skills/model-check/`: rhythm, calendar and reminders, build-agent briefs, model review.
- `skills/day-capture/`, `skills/win-star/`, `skills/raw-input-distill/`,
  `skills/error-log/`, `skills/website-queue/`: the capture set.
- `engine/calendar_write_mcp.py`: stdlib stdio MCP server, create and update only.
- `engine/test_calendar_write_mcp.py`: stdlib tests for its argument hardening (fake gog).
- `engine/weekly-review.sh`: the Sunday prompt, run from system cron.
- `engine/PINS.md`: versions it ran on and how to bump gogcli safely.
