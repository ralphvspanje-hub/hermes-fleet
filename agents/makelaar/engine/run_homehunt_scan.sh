#!/usr/bin/env bash
# Home-hunt scan cycle (cron, ~every 15 min). Polls the alert inbox + cheap scrape +
# spend-guarded Tier-3, classifies, and instant-pings new SHOW/FLAG to the user.
set -uo pipefail
APP="$HOME/home-hunt"
PY="$HOME/.hermes/hermes-agent/venv/bin/python"
set -a; . "$HOME/.hermes/profiles/makelaar/.env" 2>/dev/null || . "$HOME/.hermes/.env" 2>/dev/null || true; set +a
export HOME_HUNT_DB="${HOME_HUNT_DB:-$APP/home_hunt.sqlite}"
export HOME_HUNT_BUDGET_DB="${HOME_HUNT_BUDGET_DB:-$APP/home_hunt_budget.sqlite}"
export HOME_HUNT_MONTH="$(date +%Y-%m)"
# single-run lock (a 15-min cron must not overlap a slow scan)
exec 9>"$APP/.scan.lock"; command -v flock >/dev/null && { flock -n 9 || { echo "busy"; exit 0; }; }
cd "$APP"
"$PY" -m home_hunt.cli scan 2>>"$APP/scan.log"
