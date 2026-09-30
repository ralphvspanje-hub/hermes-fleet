#!/usr/bin/env bash
# Leak gate: run before every commit and before any push.
# Usage: scripts/scan.sh [denylist-path]
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DENY="${1:-$HOME/.hermes-fleet-denylist.txt}"
fail=0

# Scan exactly what git could commit: tracked + untracked, minus .gitignore'd paths.
cd "$ROOT"
mapfile -t FILES < <(git ls-files -co --exclude-standard | grep -v '^scripts/scan.sh$')
[[ ${#FILES[@]} -eq 0 ]] && FILES=(.gitignore)

if [[ -f "$DENY" ]]; then
  while IFS= read -r term; do
    term="${term%$'\r'}"
    [[ -z "$term" || "$term" == \#* ]] && continue
    # grep -i -F aborts on some Git Bash builds, so escape the literal and use -E.
    pat="$(printf '%s' "$term" | sed 's/[][\\.*^$+?(){}|\/-]/\\&/g')"
    if grep -niwE -- "$pat" "${FILES[@]}" >/dev/null; then
      echo "DENYLIST HIT: $term"
      grep -niwE -- "$pat" "${FILES[@]}" | head -5
      fail=1
    fi
  done < "$DENY"
else
  echo "WARN: no denylist at $DENY (pattern checks only)"
fi

check() { # label, extended regex
  if grep -nE -- "$2" "${FILES[@]}" >/dev/null; then
    echo "PATTERN HIT ($1):"; grep -nE -- "$2" "${FILES[@]}" | head -5; fail=1
  fi
}
check "IPv4"          '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b'
check "telegram id"   '-100[0-9]{7,}'
check "phone"         '\+31 ?6|\b06[- ]?[0-9]{8}\b'
check "email"         '[A-Za-z0-9._%+-]+@(gmail|outlook|hotmail|icloud|proton)\.'
check "ts.net host"   '[a-z0-9-]+\.[a-z0-9-]+\.ts\.net'
check "win user path" 'C:[\\]+Users[\\]+Ralph|/c/Users/Ralph'
check "vps home"      '/home/hermes'
check "em dash"       $'\xe2\x80\x94'
check "token-ish"     '(sk-ant-|AIza[0-9A-Za-z_-]{20}|[0-9]{8,10}:[A-Za-z0-9_-]{35})'

if command -v gitleaks >/dev/null; then
  gitleaks detect --no-git --source "$ROOT" --no-banner || fail=1
else
  echo "WARN: gitleaks not installed"; fail=1
fi

[[ $fail -eq 0 ]] && echo "SCAN CLEAN" || { echo "SCAN FAILED"; exit 1; }
