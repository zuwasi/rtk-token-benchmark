# rtk lint-script fix (workaround for rtk-ai/rtk#1489 and #2094)

A small kit that stops [rtk](https://github.com/rtk-ai/rtk) from silently changing what `npm run lint` and `pnpm lint` do when an AI coding agent runs them. Install takes one command, keeps a backup of your rtk config and can be undone.

## The problem

rtk's agent hooks (Claude Code, Droid, Cursor, Codex and others, plus our [Amp plugin](../../amp/rtk.ts)) rewrite shell commands to their `rtk` equivalents. In rtk 1.0.1, the latest release, these are all rewritten to `rtk lint`:

```
pnpm lint          -> rtk lint
pnpm run lint      -> rtk lint
npm run lint       -> rtk lint
npm run lint -- --fix -> rtk lint -- --fix
```

`rtk lint` runs rtk's own eslint call. It never reads your `package.json`, so whatever your `lint` script actually does is dropped:

- extra flags such as `--max-warnings 0` or `--report-unused-disable-directives`
- chained steps such as `pnpm check:types && eslint .`
- a different linter (Biome, oxlint), which rtk then tries to parse as ESLint JSON

The result is a **false green**: the agent sees lint pass, and CI fails. Or a working project looks broken because rtk reports a JSON parse error.

Reproduce it:

```jsonc
// package.json
{ "scripts": { "lint": "eslint --max-warnings 0" } }
```

```bash
npm run lint; echo $?   # 1 when there is a warning (correct)
rtk lint; echo $?       # 0 (what the agent runs after the rewrite)
```

## Status upstream

| | |
|---|---|
| Reported | [#1489](https://github.com/rtk-ai/rtk/issues/1489) (open), [#2094](https://github.com/rtk-ai/rtk/issues/2094) (closed as duplicate of #1489) |
| Proposed fix | [PR #2860](https://github.com/rtk-ai/rtk/pull/2860), open, not merged |
| Latest release checked | rtk 1.0.1: affected |
| `develop` checked | e542dca (2026-10-17): still affected |

Run `verify` after each rtk upgrade. Once it passes without this kit, you can uninstall it.

## What the kit does

It adds this block to rtk's own `config.toml`, using rtk's supported `[hooks] exclude_commands` setting:

```toml
# BEGIN rtk-lint-script-fix (rtk-ai/rtk#1489, #2094)
[hooks]
exclude_commands = [
  "npm run lint", "npm run-script lint", "npm rum lint", "npm urn lint", "npm lint",
  "pnpm lint", "pnpm run lint", "pnpm run-script lint",
  "npx lint", "pnpx lint", "lint",
]
# END rtk-lint-script-fix
```

Each entry also covers anything after it, so `npm run lint -- --fix` and `pnpm lint src/a.ts` are excluded too. Excluded commands run exactly as typed. Everything else is unchanged: `eslint src`, `npx eslint .` and `pnpm eslint .` still go through `rtk lint`, and `git status`, `cargo test` and the rest are still compressed.

Nothing is installed or patched in rtk or in your agent. It is one config file change, which all hooks read because they all call `rtk rewrite` / `rtk hook`.

**Trade-off:** output from your lint *script* is no longer compressed by rtk. Correct pass/fail results are worth more than the saved tokens.

## Install

You need rtk on your `PATH` (or pass its path, see below).

**Windows** (PowerShell 7 or Windows PowerShell 5.1):

```powershell
cd rtk-lint-script-fix
powershell -ExecutionPolicy Bypass -File .\install.ps1
```

Windows marks files from a downloaded zip as coming from the internet, so running `.\verify.ps1` or `.\uninstall.ps1` directly may be blocked. Either use the same `powershell -ExecutionPolicy Bypass -File …` form, or run `Get-ChildItem *.ps1 | Unblock-File` once in the folder.

**macOS, Linux, WSL:**

```bash
cd rtk-lint-script-fix
bash install.sh
```

The installer:

1. asks rtk where its config lives (`rtk config`):
   - Windows: `%APPDATA%\rtk\config.toml`
   - Linux and WSL: `~/.config/rtk/config.toml`
   - macOS: `~/Library/Application Support/rtk/config.toml`
2. creates the file if it does not exist, or backs it up as `config.toml.bak-<date>-<time>` before changing it,
3. adds the block to your existing `[hooks]` table, or appends one,
4. runs `verify` and prints the result.

Running it twice changes nothing. If your config **already has `exclude_commands`**, the installer leaves the file alone, prints the entries to add by hand and exits with code 2.

If rtk is not on `PATH` (common for Droid on Windows, which needs an absolute path in its hooks):

```powershell
.\install.ps1 -Rtk C:\tools\rtk\rtk.exe
```
```bash
bash install.sh --rtk /opt/rtk/rtk
```

Install it on every machine and environment where an agent runs rtk. WSL and Windows have separate rtk configs.

## Verify

```powershell
.\verify.ps1            # Windows
```
```bash
bash verify.sh          # macOS, Linux, WSL
```

Expected output:

```
Checking rtk 1.0.1
  ok    pnpm lint                -> (runs unchanged)
  ok    pnpm lint src/a.ts       -> (runs unchanged)
  ok    pnpm run lint            -> (runs unchanged)
  ok    npm run lint             -> (runs unchanged)
  ok    npm run lint -- --fix    -> (runs unchanged)
  ok    npm run-script lint      -> (runs unchanged)
  ok    eslint src               -> rtk lint src   (rtk still compresses this)
  ok    git status               -> rtk git status   (rtk still compresses this)
RESULT: fix active. package.json lint scripts run as written.
```

Exit code 0 means the fix is active, 1 means the bug is still present (lines marked `FAIL`), 3 means rtk was not found. You can use it in CI or a setup script.

## Uninstall

```powershell
.\uninstall.ps1
```
```bash
bash uninstall.sh
```

This removes only the marked block (after another backup). If nothing else was in the config, the file is deleted, which returns rtk to its defaults.

## Manual install

Run `rtk config` to find the file, then paste the contents of [`config-snippet.toml`](config-snippet.toml). If the file already has a `[hooks]` table, put only the `exclude_commands` line inside it. If it already has `exclude_commands`, add the entries to the existing list. Then run `verify`.

## Notes

- Tested with rtk 1.0.1 on Windows 11 (PowerShell 7.6 and Windows PowerShell 5.1) and Ubuntu 24.04 under WSL. The shell scripts use only POSIX tools (awk, sed, grep) and are written to work with macOS's bash 3.2, but were not run on a Mac.
- Users on rtk 0.37.x reported that `exclude_commands` was ignored by the hooks. `verify` tells you if your version honours it. If it shows `FAIL` after install, upgrade rtk.
- If you still use the old shell-script hook from an early `rtk init` (`~/.claude/hooks/rtk-rewrite.sh`), re-run `rtk init -g` so the hook goes through `rtk rewrite`, then run `verify`.
- `rtk lint` called directly (for example `rtk lint --max-warnings 0`) is not affected by this bug and still works.

## Files

| File | Purpose |
|---|---|
| `install.ps1`, `install.sh` | Add the fix to rtk's config, with a backup, then verify |
| `verify.ps1`, `verify.sh` | Check whether the bug is present (exit 0 = fixed) |
| `uninstall.ps1`, `uninstall.sh` | Remove the fix |
| `config-snippet.toml` | The block, for manual install |

Part of [rtk-token-benchmark](https://github.com/zuwasi/rtk-token-benchmark) by Daniel Liezrowice ([ESL](https://www.eswlab.com)). MIT licence. Not affiliated with the rtk project.
