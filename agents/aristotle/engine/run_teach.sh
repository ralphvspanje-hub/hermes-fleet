#!/usr/bin/env bash
# Aristotle lesson engine: vetted wrapper around headless Claude Code.
# Usage: run_teach.sh <onboard|lesson|feedback> <track-slug> [payload-file]
#
# Containment: writes are limited to ~/brain/teach/<slug> (cwd-locked); tools are
# file + web only (NO Bash); claude runs with a clean environment holding only the
# API key; per-track settings files are wiped every run. Slug is validated to block
# path traversal. This wrapper is the ONLY thing the teach-MCP invokes (via the
# async runner); the chat agent never gets raw exec.
set -euo pipefail

MODE="${1:?mode required: onboard|lesson|feedback}"
SLUG="${2:?track slug required}"
PAYLOAD="${3:-}"

# --- validate slug (only a-z 0-9 dash; blocks .., slashes, leading dash) ---
case "$SLUG" in
  *[!a-z0-9-]* | "" | -* ) echo "ERR invalid slug: '$SLUG'" >&2; exit 2 ;;
esac

BASE="$HOME/brain/teach"
TRACK="$BASE/$SLUG"
ENGINE="$HOME/teach-engine"
. "$ENGINE/envfile.sh"

API_KEY="$(setting ANTHROPIC_API_KEY)"
[ -n "$API_KEY" ] || { echo "ERR no ANTHROPIC_API_KEY in the environment or $ENVF" >&2; exit 3; }

MODEL="$(setting TEACH_MODEL)"; MODEL="${MODEL:-claude-opus-5}"
CAP="$(setting TEACH_MAX_TURNS)"; CAP="${CAP:-50}"
# Base URL of the lesson hub as the learner's phone reaches it (tailnet address).
HUB_URL="$(setting HUB_URL)"; HUB_URL="${HUB_URL:-http://localhost:8688}"; HUB_URL="${HUB_URL%/}"
case "$HUB_URL" in
  *localhost*) echo "WARN HUB_URL is '$HUB_URL': lesson links will not open on your phone; set it to the hub's tailnet address" >&2 ;;
esac

mkdir -p "$BASE"

# --- single-run lock per track (a retry must NOT start a 2nd concurrent Opus run) ---
exec 9>"$BASE/.lock-$SLUG" 2>/dev/null || true
if command -v flock >/dev/null 2>&1; then
  flock -n 9 || { echo "ERR busy: a generation for '$SLUG' is already running; wait for it to finish" >&2; exit 7; }
fi

[ "$MODE" = "onboard" ] && mkdir -p "$TRACK"
[ -d "$TRACK" ] || { echo "ERR track not found: '$SLUG' (onboard it first)" >&2; exit 4; }

# --- wipe settings a previous run could have planted (they could loosen permissions) ---
rm -f "$TRACK/.claude/settings.json" "$TRACK/.claude/settings.local.json"

# --- install canonical skill + overlay INTO the track (copy = stays in workspace) ---
mkdir -p "$TRACK/.claude/skills"
rm -rf "$TRACK/.claude/skills/teach"
cp -r "$ENGINE/skill/teach" "$TRACK/.claude/skills/teach"
cp -f "$ENGINE/teach-conventions.md" "$TRACK/teach-conventions.md"

# --- stage payload (mission json / difficulty / pasted results) ---
[ -n "$PAYLOAD" ] && [ -f "$PAYLOAD" ] && cp "$PAYLOAD" "$TRACK/.engine-input"

SKILLREF="Follow the canonical /teach skill exactly: read and follow ./.claude/skills/teach/SKILL.md and its referenced *-FORMAT.md files. Also apply the overlay ./teach-conventions.md (Copy-results footer + HUB_URL only). Use WebFetch/WebSearch for sources as the skill requires."

case "$MODE" in
  onboard)
    PROMPT="$SKILLREF
ONBOARD a new learning track named '$SLUG'. The learner's goal and gathered context are in ./.engine-input: read it and let it ground the mission. Do NOT create a lesson yet." ;;
  lesson)
    DIFF=""; [ -f "$TRACK/.engine-input" ] && DIFF="$(cat "$TRACK/.engine-input")"
    PROMPT="$SKILLREF
Create the NEXT lesson for track '$SLUG', following the skill (use MISSION.md + learning-records/ for the zone of proximal development). Learner difficulty signal: '${DIFF:-none}'. Save it as lessons/000N-<short-slug>.html. After writing, print exactly one line: HUB_URL: $HUB_URL/$SLUG/lessons/<filename>" ;;
  feedback)
    PROMPT="$SKILLREF
FEEDBACK step for track '$SLUG'. The learner's pasted Copy-results are in ./.engine-input: read it. Update learning-records/ per the skill to capture what was demonstrated. Do NOT create a new lesson." ;;
  *) echo "ERR unknown mode: $MODE" >&2; exit 5 ;;
esac

# --- run headless Claude Code, contained to file + web tools (no Bash) ---
# Clean environment: only the API key, nothing else from the .env or the gateway.
# Deny rules use Claude Code permission-rule syntax: ~/ = home, // = absolute
# path, a bare path = relative to the track folder.
cd "$TRACK"
set +e
OUT="$(env -i HOME="$HOME" PATH="$PATH" LANG="${LANG:-C.UTF-8}" ANTHROPIC_API_KEY="$API_KEY" \
  claude -p "$PROMPT" --model "$MODEL" --max-turns "$CAP" --permission-mode acceptEdits \
  --disallowedTools Bash "Read(~/.hermes/**)" "Read(//proc/**)" "Edit(.claude/**)" "Write(.claude/**)" \
  --allowedTools Write Edit Read Glob Grep WebFetch WebSearch \
  < /dev/null 2>&1)"
RC=$?
set -e
rm -f "$TRACK/.engine-input"
if [ $RC -ne 0 ]; then echo "$OUT" | tail -20 >&2; echo "ERR engine rc=$RC mode=$MODE track=$SLUG" >&2; exit 6; fi

# --- structured result for the async runner to parse ---
echo "$OUT" | grep -E "^HUB_URL:" || true
NEWEST="$(ls -t "$TRACK"/lessons/*.html 2>/dev/null | head -1 || true)"
[ -n "$NEWEST" ] && echo "LESSON_FILE: $NEWEST" && echo "HUB_URL: $HUB_URL/$SLUG/lessons/$(basename "$NEWEST")"
echo "ENGINE_OK mode=$MODE track=$SLUG"
