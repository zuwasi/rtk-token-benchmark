<p align="center">
  <a href="https://eswlab.com"><img src="assets/esl-logo.png" alt="ESL, Engineering Software Lab" height="80"></a>
</p>

# rtk token-savings benchmark

How many tokens does [rtk](https://github.com/rtk-ai/rtk) really save? I ran 12 everyday developer commands with and without rtk v1.0.1 and counted every output with the tokenizers of five LLM families.

<table>
  <tr>
    <td><img src="assets/daniel-liezrowice.jpg" alt="Daniel Liezrowice" width="110"></td>
    <td>
      <b>Benchmark by Daniel Liezrowice</b><br>
      Engineering Software Lab (ESL)<br>
      <a href="https://www.linkedin.com/in/liezrowice/">LinkedIn</a> · <a href="https://eswlab.com">eswlab.com</a>
    </td>
  </tr>
</table>

**Presentation (live):** **https://zuwasi.github.io/rtk-token-benchmark/**

Navigate with the large side arrows, the Home button, the keyboard (arrow keys, Home, End) or a swipe on touch screens. The deck is a single self-contained file, [`presentation.html`](presentation.html), and all 21 slides are also shown as images below.

## Slides

<p align="center"><img src="shots/slide01.png" alt="Title slide" width="100%"></p>

<table>
  <tr>
    <td><img src="shots/slide02.png" alt="About this study"></td>
    <td><img src="shots/slide03.png" alt="What rtk does"></td>
  </tr>
  <tr>
    <td><img src="shots/slide04.png" alt="Test setup"></td>
    <td><img src="shots/slide05.png" alt="The 12 commands"></td>
  </tr>
  <tr>
    <td><img src="shots/slide06.png" alt="Headline result"></td>
    <td><img src="shots/slide07.png" alt="Savings by command"></td>
  </tr>
  <tr>
    <td><img src="shots/slide08.png" alt="git status before and after"></td>
    <td><img src="shots/slide09.png" alt="pytest before and after"></td>
  </tr>
  <tr>
    <td><img src="shots/slide10.png" alt="Largest savings"></td>
    <td><img src="shots/slide11.png" alt="Where rtk adds nothing"></td>
  </tr>
  <tr>
    <td><img src="shots/slide12.png" alt="Across models"></td>
    <td><img src="shots/slide13.png" alt="Overhead"></td>
  </tr>
  <tr>
    <td><img src="shots/slide14.png" alt="Self-report vs measurement"></td>
    <td><img src="shots/slide15.png" alt="Cost"></td>
  </tr>
  <tr>
    <td><img src="shots/slide16.png" alt="Amp integration"></td>
    <td><img src="shots/slide17.png" alt="Amp results"></td>
  </tr>
  <tr>
    <td><img src="shots/slide18.png" alt="Agents compared"></td>
    <td><img src="shots/slide19.png" alt="Verdict"></td>
  </tr>
  <tr>
    <td><img src="shots/slide20.png" alt="Full results"></td>
    <td><img src="shots/slide21.png" alt="Contact"></td>
  </tr>
</table>

## Result

| Model | Tokenizer | Without rtk | With rtk | Saved |
|---|---|---:|---:|---:|
| GPT-4o | o200k_base (tiktoken) | 225,685 | 27,961 | 87.6% |
| Claude | @anthropic-ai/tokenizer | 270,527 | 32,503 | 88.0% |
| Gemini | Gemma-3 tokenizer (stand-in) | 271,603 | 33,371 | 87.7% |
| Llama 3.3 | Llama-3.1 tokenizer | 223,829 | 27,423 | 87.7% |
| Qwen3 | Qwen3-8B tokenizer | 233,509 | 29,549 | 87.3% |

The output delivered to the agent shrank from 836.7 KB to 86.3 KB (−89.7%).

| Command | Raw | With rtk | Saved |
|---|---:|---:|---:|
| `cat` 337 KB file vs `rtk read --max-lines 150` | 337.7 KB | 4.7 KB | 98.6% |
| `cat` 83 KB file vs `rtk read --max-lines 150` | 83.3 KB | 3.8 KB | 95.4% |
| `python -m pytest` (12 failures) | 8.0 KB | 948 B | 88.2% |
| `grep -rn 'unwrap()' src` | 143.6 KB | 17.4 KB | 87.9% |
| `git diff HEAD~12` | 171.7 KB | 23.5 KB | 86.3% |
| `rg -n 'pub fn' src` | 56.9 KB | 18.5 KB | 67.5% |
| `ls -la` | 3.1 KB | 1.1 KB | 63.1% |
| `cargo test` (6 failures) | 3.1 KB | 1.2 KB | 62.0% |
| `git log -40` | 22.9 KB | 9.3 KB | 59.4% |
| `git status` | 1.2 KB | 693 B | 40.4% |
| `npm test` (jest, 5 failures) | 2.2 KB | 2.2 KB | 2.4% |
| `git log --oneline -40` | 3.0 KB | 3.0 KB | 0.7% |

## Caveats

- `rtk read` passes files through unchanged by default. The file-read savings above use `--max-lines 150`, its structural preview mode.
- rtk's own `rtk gain` dashboard reported 44.9% for the same runs because it leaves out outputs larger than about 30,000 characters.
- Compression is lossy: the rtk pytest output named 10 of the 12 failures and counted the other 2.
- Added latency was 8–49 ms on quick commands and 31–146 ms on test suites and the large diff.
- Google publishes no Gemini tokenizer; Gemma-3 is used as the closest public stand-in.
- Costs in the deck use October 2026 list input prices and are illustrative, not a bill forecast.
- Tested on Windows 11. `rtk tree` failed there (it passes Linux flags to Windows `tree`) and was left out, as was `find`.

## Amp integration

rtk v1.0.1 has no Amp support, so [`amp/rtk.ts`](amp/rtk.ts) adds it as an Amp plugin. The plugin listens to Amp's `tool.call` event and asks `rtk rewrite` whether the shell command has an rtk equivalent. If it does, the plugin returns `{action: "modify"}` with the rewritten command. This is the same hook point rtk uses in Claude Code, so it applies to every thread without any prompt changes.

```powershell
copy amp\rtk.ts $env:USERPROFILE\.config\amp\plugins\rtk.ts   # rtk must be on PATH
$env:RTK_AMP_DISABLE = "1"                                     # optional: turn it off
```

The plugin was checked in a live Amp thread: `git status`, `git log`, `git diff`, `rg` and `cargo test` were all rewritten, and 6 of 7 task answers were correct from the compressed output. Amp's built-in Read, Grep and glob tools do not go through the shell, so the plugin does not affect them.

[`amp/amp_bench.py`](amp/amp_bench.py) runs a full A/B comparison, with the plugin on and off for alternate fresh threads. The same task (5 shell commands, then 7 factual questions answered as JSON) ran 3 times on each side:

| Mean of 3 threads | No rtk | rtk plugin | Change |
|---|---:|---:|---:|
| Tool output returned to the model | 127.5K chars | 55.6K chars | −56.4% |
| Context tokens processed | 508.5K | 426.2K | −16.2% |
| Answers correct (of 7) | 5, 5, 5 | 6, 7, 6 | |

Amp cuts any single tool result above 50,000 characters. Without rtk, the `git diff` and `rg` outputs hit that limit, so the model could not answer two of the questions in any run. With rtk both outputs fit. rtk's only miss was the latest commit author, in 2 of 3 runs. Raw data is in [`amp/amp_results.json`](amp/amp_results.json).

## Agents compared: Amp, Claude Code, Droid

[`agents/agent_bench.py`](agents/agent_bench.py) runs the same task and ground truth in Claude Code and Factory Droid, using rtk's official `PreToolUse` hooks passed through a per-run `--settings` file (global agent configs are not touched). 3 threads per side, each agent on its default model.

| Agent | rtk integration | Tool output | Context tokens | Correct (of 7), off → on | Cost |
|---|---|---:|---:|---|---:|
| Amp | Custom plugin ([`amp/rtk.ts`](amp/rtk.ts)) | −56.4% | −16.2% | 5·5·5 → 6·7·6 | n/a |
| Claude Code (claude-fable-5-1) | Official hook, Bash tool | +74.2% | +12.9% | 5·7·5 → 7·7·7 | +96.6% USD* |
| Droid (gpt-6.1-sol) | Official hook, Execute tool | −14.2% | −5.7% | 5·5·5 → 6·6·6 | −7.7% credits |

Every agent already limits large tool output (Amp cuts at 50K characters, Claude Code saves big outputs to a file and shows a 2 KB preview, Droid keeps about 10K). rtk's compressed output fits under those limits, so answers improved in all three agents. In Claude Code that also means more tokens, because the model reads rtk's real 23 KB diff summary instead of a 2 KB preview.

\* One cold-cache rtk run cost $1.41; the other two cost $0.58 and $0.78, against $0.43–0.52 without rtk.

Windows notes: Claude Code also has a PowerShell tool that rtk's Bash hook never sees (disabled for this test). Droid runs hooks without the user PATH, so the hook needs rtk's absolute path, and rewritten `rtk …` commands need an allowlist entry or `--auto high`.

This study compares rtk with no tool. It does not compare rtk with other output-compression tools.

## Reproduce (Windows, PowerShell 7)

Needs Git for Windows, Python 3.12+, Node 22 and Rust/Cargo.

```powershell
git clone https://github.com/zuwasi/rtk-token-benchmark
cd rtk-token-benchmark
pwsh ./setup.ps1                              # rtk binary, rtk repo, tokenizers, test suites
.venv\Scripts\python.exe bench.py             # writes results.json and out/
.venv\Scripts\python.exe build_presentation.py
```

## Files

| Path | Contents |
|---|---|
| `bench.py` | Runs every command raw and through rtk, times it, counts tokens with the 5 tokenizers |
| `make_projects.py` | Generates the pytest, cargo and jest projects with deliberate failures |
| `claude-tok/count.js` | Counts tokens with Anthropic's tokenizer |
| `build_presentation.py`, `deck_style.css` | Build `presentation.html` from `results.json`, `out/` and `assets/` |
| `index.html` | Redirects the GitHub Pages root to the presentation |
| `amp/` | Amp plugin (`rtk.ts`) and the end-to-end A/B harness (`amp_bench.py`) |
| `agents/` | Claude Code and Droid A/B harness (`agent_bench.py`) and results |
| `results.json` | Full measurements |
| `out/` | Captured stdout and stderr of every command, raw and filtered. Local paths and the user name are replaced with `[your path]`, `[usr]` and `[group]`, so a few files differ slightly from the byte counts in `results.json`, which were measured before anonymizing |
| `probes/` | Exploratory scripts used to choose the rtk invocation for each command |

## License

MIT, see [LICENSE](LICENSE). rtk itself is a separate project under its own licence: [github.com/rtk-ai/rtk](https://github.com/rtk-ai/rtk).
