#!/usr/bin/env bash
# Stops rtk from rewriting package.json "lint" scripts to `rtk lint` (rtk-ai/rtk#1489, #2094).
# Adds a marked [hooks] exclude_commands block to rtk's config.toml. Backs up an existing
# config first, never overwrites existing exclude_commands, then runs verify.sh.
# Linux, macOS and WSL. Usage: bash install.sh [--config PATH] [--rtk PATH]
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RTK="rtk"
CONFIG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2 ;;
    --rtk) RTK="$2"; shift 2 ;;
    -h|--help) sed -n '2,6p' "$0"; exit 0 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done
CUSTOM_CONFIG=0
[ -n "$CONFIG" ] && CUSTOM_CONFIG=1

BEGIN="# BEGIN rtk-lint-script-fix (rtk-ai/rtk#1489, #2094)"
END="# END rtk-lint-script-fix"
EXCLUDE='exclude_commands = [
  "npm run lint", "npm run-script lint", "npm rum lint", "npm urn lint", "npm lint",
  "pnpm lint", "pnpm run lint", "pnpm run-script lint",
  "npx lint", "pnpx lint", "lint",
]'

if [ -z "$CONFIG" ]; then
  if ! command -v "$RTK" >/dev/null 2>&1; then
    echo "rtk not found. Install rtk or pass --rtk /path/to/rtk" >&2; exit 1
  fi
  CONFIG="$(RTK_SUPPRESS_HOOK_WARNING=1 "$RTK" config 2>/dev/null | sed -n 's/^Config: //p' | head -n1 || true)"
  if [ -z "$CONFIG" ]; then
    if [ "$(uname -s)" = "Darwin" ]; then CONFIG="$HOME/Library/Application Support/rtk/config.toml"
    else CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/rtk/config.toml"; fi
  fi
fi
echo "rtk config: $CONFIG"
mkdir -p "$(dirname "$CONFIG")"

if [ ! -e "$CONFIG" ]; then
  printf '%s\n[hooks]\n%s\n%s\n' "$BEGIN" "$EXCLUDE" "$END" > "$CONFIG"
  echo "Created config with the fix."
elif grep -qxF "$BEGIN" "$CONFIG"; then
  echo "Fix is already installed. Nothing changed."
else
  # 0 = no [hooks] table, 1 = [hooks] without exclude_commands, 2 = exclude_commands already set
  state="$(awk '
    /^[[:space:]]*hooks\.exclude_commands[[:space:]]*=/ { ex=1 }
    /^[[:space:]]*\[/ { inh = ($0 ~ /^[[:space:]]*\[hooks\][[:space:]]*(#.*)?$/); if (inh) h=1; next }
    inh && /^[[:space:]]*exclude_commands[[:space:]]*=/ { ex=1 }
    END { print (ex ? 2 : (h ? 1 : 0)) }' "$CONFIG")"
  if [ "$state" = "2" ]; then
    echo "WARNING: your config already has [hooks] exclude_commands. Not changing it automatically." >&2
    echo "Add these entries to your existing exclude_commands list in $CONFIG :"
    printf '%s\n' "$EXCLUDE" | sed '1d;$d'
    exit 2
  fi
  backup="$CONFIG.bak-$(date +%Y%m%d-%H%M%S)"
  cp "$CONFIG" "$backup"
  echo "Backup: $backup"
  tmp="$(mktemp)"
  if [ "$state" = "1" ]; then
    # Multi-line values go through ENVIRON: some awks reject newlines in -v.
    B="$BEGIN" E="$END" X="$EXCLUDE" awk '
      { print }
      !done && /^[[:space:]]*\[hooks\][[:space:]]*(#.*)?$/ { print ENVIRON["B"]; print ENVIRON["X"]; print ENVIRON["E"]; done=1 }' "$CONFIG" > "$tmp"
    echo "Added exclude_commands to the existing [hooks] table."
  else
    { cat "$CONFIG"; [ -n "$(tail -c1 "$CONFIG")" ] && echo; printf '\n%s\n[hooks]\n%s\n%s\n' "$BEGIN" "$EXCLUDE" "$END"; } > "$tmp"
    echo "Appended a [hooks] table with the fix."
  fi
  cat "$tmp" > "$CONFIG"
  rm -f "$tmp"
fi

# rtk only reads its default config location, so a custom --config cannot be verified live.
if [ "$CUSTOM_CONFIG" = "0" ]; then
  exec bash "$HERE/verify.sh" --rtk "$RTK"
fi
