#!/usr/bin/env bash
# Checks that rtk no longer rewrites package.json "lint" scripts, and still rewrites direct linter calls.
# Exit code 0 = fix active, 1 = bug still present, 3 = rtk not found.
# Usage: bash verify.sh [--rtk PATH]
set -uo pipefail
RTK="rtk"
[ "${1:-}" = "--rtk" ] && RTK="$2"
if ! command -v "$RTK" >/dev/null 2>&1; then echo "rtk not found. Pass --rtk /path/to/rtk"; exit 3; fi
export RTK_SUPPRESS_HOOK_WARNING=1
echo "Checking $("$RTK" --version 2>/dev/null)"

rw() { "$RTK" rewrite "$1" 2>/dev/null | tr '\n' ' ' | sed 's/[[:space:]]*$//'; }

fail=0
for c in "pnpm lint" "pnpm lint src/a.ts" "pnpm run lint" "npm run lint" "npm run lint -- --fix" "npm run-script lint"; do
  r="$(rw "$c")"
  case "$r" in
    "rtk lint"*) printf '  FAIL  %-24s -> %s   (script body would be dropped)\n' "$c" "$r"; fail=$((fail+1)) ;;
    *) printf '  ok    %-24s -> %s\n' "$c" "${r:-(runs unchanged)}" ;;
  esac
done

check_control() {
  local r; r="$(rw "$1")"
  if [ "$r" = "$2" ]; then printf '  ok    %-24s -> %s   (rtk still compresses this)\n' "$1" "$r"
  else printf '  note  %-24s -> %s   (expected %s; rtk rewrites may be off or behave differently in this version)\n' "$1" "${r:-(not rewritten)}" "$2"; fi
}
check_control "eslint src" "rtk lint src"
check_control "git status" "rtk git status"

if [ "$fail" -gt 0 ]; then
  echo "RESULT: bug still present ($fail command(s) rewritten to rtk lint). Run install.sh, or upgrade rtk."
  exit 1
fi
echo "RESULT: fix active. package.json lint scripts run as written."
