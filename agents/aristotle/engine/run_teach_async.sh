#!/usr/bin/env bash
# Detached async runner for the teach engine.
# Spawned (detached, new session) by teach_mcp.py so it SURVIVES MCP reconnects.
# Runs the engine, records status JSON, and pushes the result to the track's topic.
# Usage: run_teach_async.sh <mode> <track> [payload-file]
#
# Settings (process env first, then the aristotle .env, see envfile.sh):
#   TELEGRAM_BOT_TOKEN  the Aristotle bot token
#   LYCEUM_CHAT_ID      the forum group's chat id (YOUR_GROUP_CHAT_ID)
#   PY                  python for the small JSON helpers (default python3)
# The topic comes from ~/brain/teach/tracks.json (thread_id -> track). With no
# binding (e.g. a brand-new track) the message goes to the group without a thread
# id, which Telegram delivers to the General topic.
set -uo pipefail

MODE="${1:?}"; SLUG="${2:?}"; PAYLOAD="${3:-}"
case "$SLUG" in
  *[!a-z0-9-]* | "" | -* ) echo "ERR invalid slug: '$SLUG'" >&2; exit 2 ;;
esac

BASE="$HOME/brain/teach"; TRACK="$BASE/$SLUG"; ST="$TRACK/.status.json"
ENGINE_DIR="$HOME/teach-engine"
. "$ENGINE_DIR/envfile.sh"
PY="$(setting PY)"; PY="${PY:-python3}"

# teach_mcp.py claimed this track with .spawn.lock before spawning us; release it
# however we exit.
trap 'rm -f "$TRACK/.spawn.lock"' EXIT

mkdir -p "$TRACK"

OUT="$(bash "$ENGINE_DIR/run_teach.sh" "$MODE" "$SLUG" ${PAYLOAD:+"$PAYLOAD"} 2>&1)"; RC=$?
[ -n "$PAYLOAD" ] && rm -f "$PAYLOAD"

# rc 7 = another run holds the per-track flock: it owns the status file and the
# notification, so leave both alone.
[ "$RC" -eq 7 ] && exit 0

URL="$(printf '%s\n' "$OUT" | grep -m1 '^HUB_URL:' | sed 's/^HUB_URL: //')"

# Which topic is this track bound to? (tracks.json bindings: thread_id -> track)
THREAD="$(SLUG="$SLUG" REG="$BASE/tracks.json" "$PY" -c "import json, os
try:
    d = json.load(open(os.environ['REG']))
    print(next((t for t, v in d.get('bindings', {}).items() if v.get('track') == os.environ['SLUG']), ''))
except Exception:
    print('')" 2>/dev/null)"

TOKEN="$(setting TELEGRAM_BOT_TOKEN)"
CHAT="$(setting LYCEUM_CHAT_ID)"
notify(){
  [ -n "$TOKEN" ] && [ -n "$CHAT" ] || return 0
  local text="$1"
  if [ -z "$THREAD" ] && [ "$MODE" != "onboard" ]; then
    text="$text (topic '$SLUG' is not bound in tracks.json)"
  fi
  set -- --data-urlencode "chat_id=$CHAT" --data-urlencode "text=$text"
  [ -n "$THREAD" ] && set -- "$@" --data-urlencode "message_thread_id=$THREAD"
  curl -s "https://api.telegram.org/bot$TOKEN/sendMessage" "$@" >/dev/null 2>&1 || true
}

if [ "$RC" -eq 0 ]; then
  printf '{"state":"done","mode":"%s","epoch":%s,"url":"%s"}\n' "$MODE" "$(date +%s)" "$URL" > "$ST"
  case "$MODE" in
    lesson)   notify "✅ Your lesson for '$SLUG' is ready: $URL" ;;
    onboard)  notify "✅ Track '$SLUG' is set up. Next: 1) create a topic named '$SLUG' 2) wire the topic (see the Aristotle README: tracks.json binding + group_topics entry + gateway restart) 3) then send a message there to begin." ;;
    feedback) notify "✅ Saved to your '$SLUG' track records, ready for the next lesson." ;;
  esac
else
  "$PY" -c "import json,time,sys;open(sys.argv[1],'w').write(json.dumps({'state':'error','mode':sys.argv[2],'epoch':int(time.time()),'error':sys.argv[3][-400:]}))" "$ST" "$MODE" "$OUT" 2>/dev/null \
    || printf '{"state":"error","mode":"%s","epoch":%s}\n' "$MODE" "$(date +%s)" > "$ST"
  notify "⚠️ Generation hit an error for '$SLUG' (rc=$RC). Ask me to retry."
fi
