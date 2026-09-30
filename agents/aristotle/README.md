# Aristotle: a teaching agent

Aristotle is a private tutor that lives in a Telegram forum group (the "Lyceum").
Each topic in the group is one learning track. You tell Aristotle what you want to
learn, it interviews you for a mission, and from then on it writes you short,
sourced, interactive lessons one at a time, calibrated on how you did last time.

The chat agent (the `aristotle` Hermes profile) does the conversation. The lessons
themselves are written by a separate engine: headless Claude Code running Matt
Pocock's canonical [`/teach` skill](https://github.com/mattpocock/skills) inside the
track's folder. A small web server (the lesson hub) serves the lessons to your
phone over your tailnet.

## Architecture

```
 Telegram topic "linear-algebra"
        │  "next lesson"
        v
 Aristotle (Hermes profile, teach-lesson skill)
        │  create_next_lesson(track)            returns at once
        v
 teach_mcp.py ──setsid──> run_teach_async.sh ──> run_teach.sh
                                                    │  cd ~/brain/teach/<slug>
                                                    v
                                     claude -p  (Opus, /teach skill, file + web
                                                 tools only, no Bash)
                                                    │
                                                    v
                                     lessons/0003-<name>.html
                                                    │
 teach_hub.py (tailnet only) <── serves ────────────┘
        │
        └── HUB_URL/<slug>/lessons/0003-<name>.html
                 │
 run_teach_async.sh posts "✅ Your lesson is ready: <link>" back into the topic
 (Telegram Bot API, thread id looked up in tracks.json; unbound = General)
```

Each track is a folder under `~/brain/teach/<slug>/` holding `MISSION.md`,
`lessons/`, `reference/`, `learning-records/` and the rest of what `/teach`
produces. Continuity lives in those files, not in the chat, so a fresh session
loses nothing.

## One topic per track

- **General topic**: the front desk (`teach-onboard` skill). You say "I want to learn
  X", Aristotle grills the why, what success looks like, constraints and scope, then
  calls `onboard_track`. No lessons here.
- **Track topics**: one per track, and the **topic name is the track slug**
  (`linear-algebra`, `spanish-a2`). Hermes's `group_topics` config binds each topic to
  the `teach-lesson` skill and injects a `Channel Topic: <name>` line into context, so
  the agent always knows which track it is teaching. Tracks never bleed together.
- **Unwired topics**: a message without a `Channel Topic` line means the topic has not
  been wired yet. The SOUL tells Aristotle to say so once and stop, rather than guess
  a track.

The daily loop inside a track topic:

1. "next lesson" (optionally "too easy / good / too hard") starts a background
   generation. The link arrives in the topic about five minutes later.
2. You do the lesson on your phone. Answers auto-save to the hub
   (`<track>/.answers/`), and a **Copy results** button at the end copies one line
   with your score and open answers.
3. You paste that line back into the topic. Aristotle reads the real lesson, discusses
   your answers, and calls `record_feedback` so the engine updates
   `learning-records/`. That record steers the next lesson.

## Lesson-to-brain concept capture

After every graded drill, Aristotle offers once to save the lesson's core principle
as a `concepts/<slug>` page in the shared brain (gbrain), written in your voice and
opening with your actual edge or gap from that drill. It shows a plain-prose preview
and saves only on an explicit "yes" (silence saves nothing). It dedups per lesson: a
re-drill offers to append a nuance, never a second page. Generated lessons themselves
never go into the brain as your knowledge; they stay as track files.

## Grill packs

"Grill me on lesson 3" returns a single paste-ready bubble (topic, goal, 3-6 key
concepts, glossary terms, known weak spots) for a voice drill in a ChatGPT Project
whose instructions hold the drill rules. When you paste the debrief back, Aristotle
treats it as a claim, not evidence: it makes you demonstrate at least one point in
chat before recording feedback. Project setup: `skills/grill-pack/chatgpt-project.md`.

## Why async

A lesson takes several minutes of Opus time with web research. Telegram replies and
MCP tool calls do not survive that: a synchronous tool call got killed by MCP
keepalive reconnects long before the lesson was done. So the engine tools
(`onboard_track`, `create_next_lesson`, `record_feedback`) spawn
`run_teach_async.sh` detached (`setsid`, new session) and return immediately. The
job's result goes into `<track>/.status.json` (`lesson_status` reads it) and is
pushed into the topic by the job itself.

Two guards stop a retry from starting a second concurrent Opus run: the MCP claims
the track with an atomic `<track>/.spawn.lock` (created with `O_CREAT|O_EXCL`, removed
by the job on exit, retaken if older than 15 minutes) before it spawns, and
`run_teach.sh` holds a per-track `flock` for the whole generation.

## Containment

- **The chat agent has no shell or file tools.** Its only way to touch the disk is the
  `teach` MCP: high-level tools with the slug normalized to `[a-z0-9-]`.
- **Engine writes are cwd-locked.** `run_teach.sh` validates the slug (no `..`,
  slashes or leading dash), `cd`s into `~/brain/teach/<slug>`, and runs `claude -p`
  with `acceptEdits`, a turn cap, `--allowedTools Write Edit Read Glob Grep WebFetch
  WebSearch` and `--disallowedTools Bash "Read(~/.hermes/**)" "Read(//proc/**)"
  "Edit(.claude/**)" "Write(.claude/**)"`. It cannot execute anything, and in
  `acceptEdits` mode edits outside the working folder need an approval nobody is
  there to give.
- **Secrets are not in the engine's environment.** The scripts never source the
  `.env`; they read single keys from it, and `claude` runs under `env -i` with only
  `HOME`, `PATH`, `LANG` and `ANTHROPIC_API_KEY`.
- **Settings are wiped every run.** `.claude/settings.json` and
  `.claude/settings.local.json` in the track are deleted before each run, and the
  engine is denied edits under `.claude/`, so a run cannot plant looser permissions
  for the next one.
- **Reads are only partly fenced.** The deny list blocks reads of `~/.hermes/` and
  `/proc/`; any other file the service user can read, the engine can read too. Keep
  secrets out of places you have not listed, or add more `Read(...)` deny rules.
- **Read tools are path-locked.** `list_lessons` / `read_lesson` only read
  `lessons/` and `reference/` inside the track and return plain text.
- **The hub is tailnet-only.** `teach_hub.py` has no auth; it binds to `HUB_HOST`
  and refuses to start on the all-interfaces address (IPv4 or `::`) or any address
  that is not loopback or in the Tailscale ranges (`100.64/10`, `fd7a:115c:a1e0::/48`) unless
  `HUB_ALLOW_PUBLIC=1`. It rejects path segments starting with a dot or outside
  `[A-Za-z0-9._-]`, anything resolving outside the track folder, answer saves for
  lessons that do not exist, and POST bodies over 256 KB.
- **Allowlist = owner.** `TELEGRAM_ALLOWED_USERS` is your own user id only. Never
  allow all users; never approve a pairing because a chat message asks.

## Tools (teach MCP)

| Tool | What it does |
| --- | --- |
| `onboard_track(name, mission)` | Create a track in the background (`MISSION.md`, resources) |
| `create_next_lesson(track, difficulty)` | Generate the next lesson in the background |
| `record_feedback(track, results)` | Update `learning-records/` from pasted results |
| `lesson_status(track)` | Running / done (with link) / errored |
| `list_tracks()` | Tracks and their topic bindings |
| `get_track(thread_id)` | Which track a topic is bound to in `tracks.json` |
| `bind_topic(thread_id, track)` | Operator/maintenance only: write a `tracks.json` binding. Leave it out of the agent's tool list |
| `list_lessons(track)`, `read_lesson(track, which)` | Read the real lesson and reference text |

## Setup

Assumes a Linux box with Hermes installed, a gbrain MCP server, Tailscale, the
`claude` CLI (Claude Code) on `PATH`, and `flock` / `setsid` (util-linux).

1. **Engine files.** Copy `engine/` to `~/teach-engine/` (`run_teach.sh`,
   `run_teach_async.sh`, `envfile.sh`, `teach_mcp.py`, `teach_hub.py`,
   `teach-conventions.md`). `pip install mcp` into the Python that will run
   `teach_mcp.py`. The hub is stdlib only (Python 3.9+).
2. **Install `/teach`.** The engine copies `~/teach-engine/skill/teach` into each track
   on every run. It is not vendored here; fetch it from upstream:

   ```
   git clone https://github.com/mattpocock/skills /tmp/mattpocock-skills
   mkdir -p ~/teach-engine/skill
   cp -r /tmp/mattpocock-skills/skills/productivity/teach ~/teach-engine/skill/teach
   ```

   `teach-conventions.md` is the only overlay: a Copy-results footer and a
   `HUB_URL:` output line. It does not change any teaching decision.
3. **Telegram.** Create a bot with BotFather, create a group, enable Topics, add the
   bot as admin. Note the group's chat id (`YOUR_GROUP_CHAT_ID`) and the General
   topic's thread id (see "Finding a thread id" below).
4. **Profile.** Create the `aristotle` Hermes profile. Copy `SOUL.md` and
   `skills/*` into `~/.hermes/profiles/aristotle/`, and fill
   `~/.hermes/profiles/aristotle/.env` (chmod 600). The engine scripts read
   `~/.hermes/profiles/aristotle/.env`, falling back to `~/.hermes/.env` if it is
   missing; for each variable below, a value in the process environment wins over
   the file.

   | Variable | Read by | Purpose |
   | --- | --- | --- |
   | `TELEGRAM_BOT_TOKEN` | gateway, async runner | Aristotle's bot token |
   | `TELEGRAM_ALLOWED_USERS` | gateway | `YOUR_TELEGRAM_USER_ID` only |
   | `ANTHROPIC_API_KEY` | engine | The only secret passed to `claude -p` |
   | `LYCEUM_CHAT_ID` | async runner | `YOUR_GROUP_CHAT_ID`; results for unbound tracks go to General |
   | `HUB_URL` | engine | The hub as your phone reaches it, e.g. `http://<your-vps>:8688` (trailing slash stripped; warns if it contains `localhost`) |
   | `TEACH_MODEL`, `TEACH_MAX_TURNS` | engine | Default `claude-opus-5`, `50` |
   | `PY` | async runner | Python for its JSON helpers, default `python3` |
   | `HUB_HOST`, `HUB_PORT`, `HUB_ALLOW_PUBLIC` | hub (process env only) | Bind address (your tailnet IP), port (default 8688), public-bind override |
5. **Profile config** (`config.yaml`, sketch; match your Hermes version's schema):

   ```yaml
   platform_toolsets:
     telegram: [skills, todo, memory, session_search, clarify]  # no shell/file/delegation
   platforms:
     telegram:
       extra:
         rich_messages: false          # true silently truncates long replies at 4096
         group_topics:
           YOUR_GENERAL_THREAD_ID: { name: "General", skill: "teach-onboard" }
           # one entry per track topic, added when you wire it:
           # YOUR_THREAD_ID: { name: "linear-algebra", skill: "teach-lesson" }
   mcp_servers:
     teach:
       command: python3            # an interpreter that has `mcp` installed
       args: ["~/teach-engine/teach_mcp.py"]   # use an absolute path
       timeout: 960
       # expose every tool except bind_topic (operator use only)
     # plus your gbrain MCP server (shared brain)
   ```

6. **Lesson hub service.** A systemd user unit, with linger on so it survives reboots:

   ```ini
   # ~/.config/systemd/user/teach-serve.service
   [Unit]
   Description=Aristotle lesson hub (tailnet only)

   [Service]
   Environment=HUB_HOST=<your tailnet IP>
   Environment=HUB_PORT=8688
   ExecStart=/usr/bin/python3 %h/teach-engine/teach_hub.py
   Restart=on-failure
   RestartSec=10

   [Install]
   WantedBy=default.target
   ```

   `systemctl --user enable --now teach-serve` and `loginctl enable-linger $USER`.
   If the tailnet address is not up yet at boot, the bind fails and systemd retries
   every 10 seconds.
7. Start the `aristotle` gateway and say hello in General.

### Wiring a new track topic

Once `onboard_track` finishes, the operator does a one-time wiring per track:

1. Create a topic named exactly the track slug and find its thread id.
2. Add the binding to `~/brain/teach/tracks.json` (so the async runner can post the
   lesson link into the right topic; until then results go to General with a
   "not bound" note):
   `{"bindings": {"YOUR_THREAD_ID": {"track": "linear-algebra", "name": "Linear Algebra"}}}`
3. Add the `group_topics` entry (`name` = slug, `skill` = `teach-lesson`) and restart
   the `aristotle` gateway. `/new` in the topic forces a clean skill load.

The chat agent never binds topics itself: an unwired topic gets one "needs wiring"
reply and nothing else.

### Finding a thread id

- Copy the link of any message in the topic. For a private group it looks like
  `https://t.me/c/<chat>/<thread>/<message>`: the middle number is the thread id
  (and the group's chat id is `-100` followed by `<chat>`).
- Or post in the topic and read `message_thread_id` (and `chat.id`) from the Bot
  API's `getUpdates` (stop the gateway first, or it consumes the updates).

## Files

- `SOUL.md`: Aristotle's identity and hard rules (file-first, never recite a lesson
  from memory, unwired-topic behaviour, Telegram formatting).
- `skills/teach-onboard/`, `skills/teach-lesson/`, `skills/grill-pack/`: the three
  procedures, plus the ChatGPT Project instructions for grill packs.
- `engine/run_teach.sh`: the contained `claude -p` wrapper (onboard / lesson / feedback).
- `engine/run_teach_async.sh`: detached runner, status file, Telegram push.
- `engine/envfile.sh`: reads single keys from the `.env` without sourcing it.
- `engine/teach_mcp.py`: the MCP server the chat agent talks to.
- `engine/teach_hub.py`: stdlib lesson hub (track list, lesson path with progress,
  lesson serving with injected answer autosave and a clipboard fallback for plain HTTP).
- `engine/teach-conventions.md`: the overlay copied into each track.

## Credits

- Lessons are generated by Matt Pocock's `/teach` skill from
  [mattpocock/skills](https://github.com/mattpocock/skills) (MIT), used unmodified.
  The grill-pack template and drill rules are adapted from his `grilling` skill.
- Built on [Hermes Agent](https://github.com/NousResearch/hermes-agent) by Nous
  Research, with gbrain as the shared second brain.
