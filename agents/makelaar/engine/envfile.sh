# Sourced by run_homehunt_browse.sh (not executed directly).
# Reads single keys from the makelaar .env WITHOUT sourcing it: sourcing would put
# every secret in the file into the environment of whatever runs next.

ENVF="$HOME/.hermes/profiles/makelaar/.env"
[ -f "$ENVF" ] || ENVF="$HOME/.hermes/.env"

# envval KEY: value of KEY in $ENVF. Handles `export `, quotes, CRLF, ` # comments`.
envval() {
  local line v
  line="$(grep -E "^[[:space:]]*(export[[:space:]]+)?$1[[:space:]]*=" "$ENVF" 2>/dev/null | tail -n1)" || true
  [ -n "$line" ] || return 0
  v="${line#*=}"
  v="${v%$'\r'}"
  v="${v#"${v%%[![:space:]]*}"}"
  case "$v" in
    \"*) v="${v#\"}"; v="${v%%\"*}" ;;
    \'*) v="${v#\'}"; v="${v%%\'*}" ;;
    *) v="${v%%[[:space:]]#*}"; v="${v%"${v##*[![:space:]]}"}" ;;
  esac
  printf '%s' "$v"
}

# setting KEY: the process environment wins; the env file is the fallback.
setting() {
  local cur="${!1:-}"
  if [ -n "$cur" ]; then printf '%s' "$cur"; else envval "$1"; fi
}
