#!/usr/bin/env bash
# Sunday weekly review prompt into the owner's Hermes DM. TRUSTED layer (system cron).
# Fixed text, no LLM call, so it cannot fail on a model/API hiccup and holds no action power.
# The user's reply lands in the normal gateway session and is handled by the weekly-review skill.
#
# Install at ~/.hermes/scripts/weekly-review.sh and schedule it from the user crontab, e.g.
#   CRON_TZ=UTC   # your IANA timezone; otherwise cron runs in the system zone
#   0 18 * * 0 $HOME/.hermes/scripts/weekly-review.sh
#
# Env file: $HERMES_ENV_FILE, default ~/.hermes/.env. Log: $WEEKLY_REVIEW_LOG, default next to
# this script. Reads from the env file (single keys, never sourced, so no other secret enters the env):
#   TELEGRAM_BOT_TOKEN   the default profile's bot token
#   OWNER_CHAT_ID        YOUR_CHAT_ID (your DM with the bot = your Telegram user id)
#
# Edit the questions to match the weekly practice and standing quest in your goals/current page.
set -uo pipefail
export PATH="/usr/local/bin:/usr/bin:/bin:$HOME/.local/bin"
ENV_FILE="${HERMES_ENV_FILE:-$HOME/.hermes/.env}"
LOG="${WEEKLY_REVIEW_LOG:-$(dirname "$0")/weekly-review.log}"
TS="$(date -u +'%Y-%m-%d %H:%M UTC')"

envval() { grep -E "^$1=" "$ENV_FILE" | tail -n1 | cut -d= -f2- | tr -d '\r"'"'"; }
TOKEN="$(envval TELEGRAM_BOT_TOKEN)"
CHAT="$(envval OWNER_CHAT_ID)"
if [ -z "$TOKEN" ] || [ -z "$CHAT" ]; then
  echo "[$TS] weekly review NOT sent: TELEGRAM_BOT_TOKEN or OWNER_CHAT_ID missing in $ENV_FILE" >> "$LOG"
  exit 1
fi

# Question 2 is an example standing quest (collecting unsolved problems); replace it with yours.
read -r -d '' TEXT <<'MSG' || true
Sunday review - keep it light, a voice note is perfect.

1. Did you do your weekly practice this week? What did it teach you?
2. Any real, unsolved problem you (or someone around you) bumped into this week? One line is plenty.

That's it, or 'skip'.
MSG

if curl -sS -f -m 20 "https://api.telegram.org/bot${TOKEN}/sendMessage" \
  --data-urlencode "chat_id=${CHAT}" --data-urlencode "text=${TEXT}" >/dev/null 2>>"$LOG"; then
  echo "[$TS] weekly review sent" >> "$LOG"
else
  rc=$?
  echo "[$TS] weekly review FAILED (curl exit $rc)" >> "$LOG"
  exit 1
fi
