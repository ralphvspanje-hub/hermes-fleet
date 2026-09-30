# Makelaar: rental-listing scout

Makelaar ("estate agent" in Dutch) is a home-hunt scout. A scheduled engine collects
rental listings, drops the ones that break hard rules, flags likely scams, scores the
rest, and pings the good ones to Telegram. A chat agent (the `makelaar` Hermes profile)
sits on top with a small MCP toolset: show recent listings, show one, mark a status,
trigger a scan, report spend.

It **finds and filters only**. It never messages a landlord, applies, or pays.

The example market is Amsterdam: the neighbourhood tiers in `geo.py`, the phrase lists
(Dutch + English) in `phrases.py`, and the PDOK geocoder are Dutch-specific. Swap
those for your own city.

## Pipeline

```
 sources ──> normalize ──> classify ─────────────────────────────> refine ──> store ──> notify
 (email     (price,        filters.py   scam.py      scoring.py    (worksite   (SQLite  (Telegram
  alerts,    housing        hard drops   reject/flag  0-100 + why   distance,   dedupe   instant
  HTML,      type, move-    (reg., sub-                             geocode,    + status) ping or
  rendered,  in date)       let, price,                             detail                 digest)
  browse)                   area, ...)                              pages)
```

- **Sources** (`home_hunt/sources/`): each implements `fetch() -> list[Listing]` and
  registers a name. Built in:
  - `email_alerts`: reads saved-search alert emails over IMAP (Tier 1, the default).
    Listings from the example sender carry the source name `example_alerts`.
  - `example`: an HTML scraper template (Tier 1).
  - `example_live`: the same parser fed by a headless Playwright render (Tier 2).
  - `browse`: headless Claude Code + Playwright MCP browses a page (logged in if
    needed) and writes JSON (Tier 3, paid, capped by `SpendGuard`).
- **Normalize** (`normalize.py`): price text to int, room vs whole-home, move-in date.
- **Classify** (`classify.py`): `filters.hard_drop_reason` → `scam.assess` →
  `scoring.score`, giving a `SHOW`, `FLAG` (shown with a warning) or `DROP` verdict.
- **Refine** (`pipeline.py`, all optional): distance to your worksite with a transit
  rescue (`worksite.py`, `transit.py`), street-name geocoding for postcode-less
  listings, reading detail pages for hidden dealbreakers (`details.py`), and a Tier-3
  walk-time check for the optional commuter-city exception (`commute.py`).
- **Store** (`store.py`): SQLite dedupe plus per-listing status
  (new/interested/contacted/dismissed/viewing).
- **Notify** (`notify.py`): Telegram Bot API, split on line boundaries under 4096 chars.

Site-specific scrapers for Dutch rental sites existed in the original but are not
published: check each site's terms before scraping. Saved-search alert emails are the
most reliable and terms-friendly source.

## Adding a source

1. Copy `home_hunt/sources/example_site.py`, set `name`, `search_url`, `base_url`, and
   adapt `select_cards` / `card_to_listing` to the site's markup.
2. Save a captured results page under `tests/fixtures/` and write a parser test
   (see `tests/test_example_site.py`).
3. Import the module in `home_hunt/sources/__init__.py` so it registers.
4. Enable it with `HOME_HUNT_SOURCES=email_alerts,<name>`.

For alert emails, add `(source_name, (sender_domain,))` to `_GENERIC_SENDERS` in
`sources/email_alerts.py`, or write a bespoke `EmailParser` subclass and put it first
in the parser list.

## Containment

Makelaar is the most exposed agent in the fleet: everything it reads is untrusted
scraped or emailed text. So:

- **Never acts on listings.** No messages, applications, or payments. The MCP tools
  only read the store, update a local status, start a scan, or report spend.
  `draft.py` can produce a Dutch intro text for the user to send themselves, but the
  pipeline does not call it by default and the agent never sends anything.
- **gbrain read-only.** It can read the shared brain, never write to it.
- **Listing text is data, never instructions** (see `SOUL.md`). Addresses passed to
  the browse engine are sanitized first (`commute._sanitize_address`).
- **Tier-3 browse is contained**: `engine/run_homehunt_browse.sh` locks headless
  Claude Code to its workdir with only `Read`, `Write` and the Playwright MCP, a
  single-run lock, and a login session pre-seeded from a file (the agent never sees
  credentials). Spend is capped per month by `SpendGuard` (`HOME_HUNT_MONTHLY_CAP`,
  default EUR 50). The script never sources the `.env`: it reads single keys
  (`engine/envfile.sh`) and runs `claude` under `env -i` with only `ANTHROPIC_API_KEY`,
  so the Telegram token and IMAP password never reach the browsing agent.
- `@playwright/mcp` is pinned (`engine/playwright-mcp.json`); bump it deliberately.
  Chromium runs with `--no-sandbox` because its sandbox needs unprivileged user
  namespaces, which hardened servers (e.g. Ubuntu's AppArmor default) deny to a
  service user; the containment comes from the tool allowlist and the clean env.
- The chat agent has no shell or file tools; it gets the `homehunt` MCP plus read-only gbrain search/get tools, nothing else.

## Configuration

Decision thresholds live in `home_hunt/config.py` (`Config`): rent ceilings (example
values), `income_eur` (your gross yearly income; `0` disables the max-income filter),
`allow_shared`, `max_commute_km`, and `exclude_household_tags` (optional household
exclusions, empty by default; available tags: `"women_only"`, `"student_only"`).
The neighbourhood tiers in `geo.py` are an example ranking: replace them with your
own. `transit.DIRECT_STATIONS` ships empty (no transit rescue); fill it with stations
that have a direct line to your worksite, following the commented format example.

The commuter-city exception is optional and off by default. It is for e.g. a nearby
city with a direct train to your worksite: set `HOME_HUNT_COMMUTER_CITIES` (e.g.
`haarlem`) to keep listings within about a 10-minute walk of that city's Centraal
station and exclude the rest of the city. `"<city> centraal"` is always recognised;
add near-station street names/postcodes to `geo._NEAR_CENTRAAL` (ships empty, with a
format comment). With `HOME_HUNT_COMMUTE=1` the browse engine also confirms the walk
time on a map.

Runtime settings come from environment variables:

| Variable | Purpose |
| --- | --- |
| `HOME_HUNT_TG_TOKEN` | Telegram bot token for pings |
| `HOME_HUNT_TG_CHAT` | Telegram chat id to ping (`YOUR_TELEGRAM_USER_ID`) |
| `HOME_HUNT_IMAP_HOST`, `HOME_HUNT_IMAP_USER`, `HOME_HUNT_IMAP_PASSWORD` | Alert inbox (use a dedicated mailbox and an app password) |
| `HOME_HUNT_DB` | Listing store path (default `home_hunt.sqlite`) |
| `HOME_HUNT_SOURCES` | Comma-separated enabled sources (default `email_alerts`) |
| `HOME_HUNT_BUDGET_DB` | Spend-guard database (default `home_hunt_budget.sqlite`) |
| `HOME_HUNT_MONTH` | Budget month key `YYYY-MM` (default: the current month) |
| `HOME_HUNT_MONTHLY_CAP` | Monthly Tier-3 spend cap in EUR (default `50`) |
| `HOME_HUNT_WORKSITE` | Worksite as `"lat,lon"`; unset disables the commute filter |
| `HOME_HUNT_WORK_DISTANCE` | Worksite-distance refine: `1` = on (default, needs `HOME_HUNT_WORKSITE`); any other value turns it off |
| `HOME_HUNT_TRANSIT` | Transit rescue/boost: `1` = on (default); any other value turns it off |
| `HOME_HUNT_GEOCODE` | Street-name geocoding: `1` = on (default); any other value turns it off |
| `HOME_HUNT_READ_DETAILS` | Detail-page reads: `1` = on (default); any other value turns it off |
| `HOME_HUNT_COMMUTER_CITIES` | Comma-separated commuter cities for the near-Centraal exception (default empty = off) |
| `HOME_HUNT_COMMUTE` | `1` enables the paid Tier-3 walk-time check for commuter cities (default off) |
| `HOME_HUNT_BROWSE_URL` | Results page for the `browse` source |
| `HOME_HUNT_BROWSE_SOURCE` | Source name stamped on browsed listings (default `browse`) |
| `HOMEHUNT_MODEL`, `HOMEHUNT_MAX_TURNS` | Model and turn cap for the browse engine |
| `ANTHROPIC_API_KEY` | Needed by the browse engine and `draft.py` |

The engine scripts expect the code at `~/home-hunt` and load secrets from
`~/.hermes/profiles/makelaar/.env` (chmod 600). Run `engine/run_homehunt_scan.sh`
from cron (e.g. every 15 minutes) and register `engine/homehunt_mcp.py` as the
profile's MCP server.

### Deploy prerequisites

- The engine scripts run the Hermes venv python at
  `$HOME/.hermes/hermes-agent/venv/bin/python`; edit `PY=` in
  `engine/run_homehunt_scan.sh` to use another interpreter.
- Live runs need `pip install -e ".[live]"` (requests, anthropic, mcp) in that
  interpreter; `example_live` also needs `".[browser]"` plus `playwright install chromium`.
- The Tier-3 browse engine needs the `claude` CLI on `PATH` and `npx` (it launches
  `@playwright/mcp`).
- Env fallback: both scripts use `~/.hermes/profiles/makelaar/.env`, falling back to
  `~/.hermes/.env` if the profile file is missing. The scan script sources it for the
  Python engine (which needs the Telegram and IMAP settings); the browse script only
  reads single keys from it (process environment wins over the file).

## Files

- `home_hunt/`: the engine package (`python -m home_hunt.cli classify|scan|digest`).
- `engine/`: MCP server, scan/browse shell wrappers, Playwright MCP config.
- `SOUL.md`: the chat agent's identity and hard rules.
- `skills/listing-actions/SKILL.md`: how the agent routes chat requests to MCP tools.

## Running the tests

```
python -m venv .venv
.venv/bin/pip install -e ".[dev]"      # Windows: .venv\Scripts\pip
.venv/bin/python -m pytest -q
```

The tests are hermetic: every network, browser, IMAP and LLM call is injected.
