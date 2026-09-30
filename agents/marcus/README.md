# Marcus: a Stoic corner

Marcus is a small Telegram agent with one job: answer through a Stoic lens, grounded
in real texts. You bring a struggle, a decision or a question about Stoicism; Marcus
finds a fitting passage from Marcus Aurelius, Epictetus or Seneca, quotes it with a
citation, and ties it to your situation in a few plain sentences. It saves nothing
unless you ask.

## How it works

```
 Telegram DM  ->  Hermes profile `marcus`  ->  stoic-lens skill
                                                   |
                          gbrain search (source_id "meditations" / "stoa")
                                                   |
                                     cited answer, quote in a blockquote

 "save this"  ->  one page at stoa/<slug> in the default brain (on request only)
```

- The `marcus` profile has its own bot, [SOUL.md](SOUL.md) persona and the
  [stoic-lens](skills/stoic-lens/SKILL.md) skill, which owns drawer routing, citation
  rules and the save procedure.
- Two isolated gbrain drawers hold the texts: `meditations` (Marcus Aurelius) and
  `stoa` (Epictetus and Seneca). Queries must pass the `source_id`.
- Saving is explicit only. A reflection goes to the `stoa/` folder inside the default
  `brain` source, never into the read-only `stoa` drawer.

## The corpus

Use public-domain translations only; do not load in-copyright translations into the
drawers. A ready-made option is
[stoa-brain](https://github.com/ralphvspanje-hub/stoa-brain): 682 Stoic passages
from Marcus Aurelius, Epictetus and Seneca, chunked, cited, and pre-embedded for
semantic search. Its vector store is a numpy array, so there is no database to
install and no API key. Its `corpus/meditations/` (412 passages) and `corpus/stoa/`
(270 passages) folders hold one Markdown file per passage, which map onto the two
drawers above.

## Setup

1. Create a Hermes profile named `marcus` with its own Telegram bot token.
2. Copy `SOUL.md` into the profile and `skills/stoic-lens/` into its skills folder.
3. Connect gbrain as an MCP server and import the passages into two sources,
   `meditations` and `stoa`.
4. Set the Telegram allowlist to `YOUR_TELEGRAM_USER_ID` only.
5. Give the profile a narrow toolset: gbrain search and save, no shell and no file
   access.
6. Start a new session after installing the skill so it loads.

## Design notes

- **A separate bot, not a skill on your main agent.** Marcus has a dedicated voice
  and a narrow corpus, and the Stoic lens is its default mode rather than something
  invoked now and then. It is its own profile rather than a topic router on a shared
  bot.
- **Saving is deliberately not Marcus's job.** Day logs, wins and raw input belong to
  the main agent; Marcus points you there.
- **Never quote from memory.** Every quote must come from a search result in the
  same turn; empty retrieval means Marcus says so and speaks in its own words.
