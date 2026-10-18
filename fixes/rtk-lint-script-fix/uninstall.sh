#!/usr/bin/env bash
# Removes the block added by install.sh from rtk's config.toml (backs it up first).
# Deletes the file if nothing else is left in it.
# Usage: bash uninstall.sh [--config PATH] [--rtk PATH]
set -euo pipefail
RTK="rtk"
CONFIG=""
while [ $# -gt 0 ]; do
  case "$1" in
    --config) CONFIG="$2"; shift 2 ;;
    --rtk) RTK="$2"; shift 2 ;;
    *) echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done
BEGIN="# BEGIN rtk-lint-script-fix (rtk-ai/rtk#1489, #2094)"
END="# END rtk-lint-script-fix"

if [ -z "$CONFIG" ]; then
  if command -v "$RTK" >/dev/null 2>&1; then
    CONFIG="$(RTK_SUPPRESS_HOOK_WARNING=1 "$RTK" config 2>/dev/null | sed -n 's/^Config: //p' | head -n1 || true)"
  fi
  if [ -z "$CONFIG" ]; then
    if [ "$(uname -s)" = "Darwin" ]; then CONFIG="$HOME/Library/Application Support/rtk/config.toml"
    else CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/rtk/config.toml"; fi
  fi
fi

[ -e "$CONFIG" ] || { echo "No config at $CONFIG. Nothing to remove."; exit 0; }
grep -qxF "$BEGIN" "$CONFIG" || { echo "Fix is not installed in $CONFIG. Nothing changed."; exit 0; }

backup="$CONFIG.bak-$(date +%Y%m%d-%H%M%S)"
cp "$CONFIG" "$backup"
tmp="$(mktemp)"
awk -v b="$BEGIN" -v e="$END" '
  $0 == b { skip=1; next }
  skip && $0 == e { skip=0; next }
  !skip { lines[++n] = $0 }
  END { while (n > 0 && lines[n] ~ /^[[:space:]]*$/) n--; for (i = 1; i <= n; i++) print lines[i] }' "$CONFIG" > "$tmp"

if [ ! -s "$tmp" ]; then
  rm -f "$tmp" "$CONFIG"
  echo "Removed the fix. The config held nothing else, so it was deleted (backup: $backup)."
else
  cat "$tmp" > "$CONFIG"
  rm -f "$tmp"
  echo "Removed the fix from $CONFIG (backup: $backup)."
fi
