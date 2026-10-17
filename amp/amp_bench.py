"""End-to-end Amp benchmark: the same task, with the rtk Amp plugin on and off.

Each run is a fresh `amp -x` thread. The plugin is switched off for a run by setting
RTK_AMP_DISABLE=1 in Amp's environment, so everything else (model, prompt, repo) is identical.
Runs alternate on/off to spread any drift across both conditions.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("RTK_BENCH_REPO", os.path.join(os.path.dirname(HERE), "repo"))
RSPROJ = os.environ.get("RTK_BENCH_RSPROJ", os.path.join(os.path.dirname(HERE), "work", "rsproj"))
RUNS = int(os.environ.get("RUNS_PER_SIDE", "3"))
OUT = os.path.join(HERE, "runs")

PROMPT = f"""You are being benchmarked. Use only the shell tool. Run exactly these commands, one per tool call,
in this order, from the working directory unless told otherwise. Do not run any other command and do not
read files any other way.

1. git status
2. git log -40
3. git diff HEAD~12
4. rg -n "pub fn" src
5. cargo test   (run it with the working directory set to {RSPROJ})

Then answer from the command output alone, as a single JSON object and nothing else:
{{"modified_not_staged": <int>, "untracked_entries": <int>, "latest_commit_author": "<name>",
"oldest_commit_author_of_40": "<name>", "diff_files_changed": <int>, "rg_files_with_pub_fn": <int>,
"cargo_failed_tests": <int>}}
If the output does not let you determine a value, use null."""

TRUTH = {
    "modified_not_staged": 10,
    "untracked_entries": 9,
    "latest_commit_author": "Nicolas Le Cam",
    "oldest_commit_author_of_40": "aesoft",
    "diff_files_changed": 42,
    "rg_files_with_pub_fn": 142,
    "cargo_failed_tests": 6,
}


def score(answer_text):
    m = re.search(r"\{.*\}", answer_text or "", re.S)
    if not m:
        return {}, 0
    try:
        ans = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {}, 0
    ok = 0
    for k, v in TRUTH.items():
        got = ans.get(k)
        if isinstance(v, str):
            ok += isinstance(got, str) and got.strip().lower() == v.lower()
        else:
            ok += got == v
    return ans, ok


def run_once(side, idx):
    env = dict(os.environ)
    if side == "off":
        env["RTK_AMP_DISABLE"] = "1"
    else:
        env.pop("RTK_AMP_DISABLE", None)
    t0 = time.time()
    # A multi-line prompt does not survive cmd.exe quoting, so call the binary directly.
    amp = shutil.which("amp") or "amp"
    p = subprocess.run([amp, "-x", PROMPT, "--stream-json", "--no-archive-after-execute"],
                       cwd=REPO, env=env, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=900)
    wall = time.time() - t0
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"{side}_{idx}.jsonl"), "w", encoding="utf-8") as f:
        f.write(p.stdout)
    if p.returncode != 0 and not p.stdout.strip():
        print("amp failed:", p.stderr[-800:], file=sys.stderr)

    usage = {"input": 0, "cache_write": 0, "cache_read": 0, "output": 0}
    tool_chars, commands, answer, thread, turns, error = 0, [], "", None, 0, None
    for line in p.stdout.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        thread = ev.get("session_id", thread)
        msg = ev.get("message") or {}
        if ev.get("type") == "assistant":
            u = msg.get("usage") or {}
            usage["input"] += u.get("input_tokens", 0)
            usage["cache_write"] += u.get("cache_creation_input_tokens", 0)
            usage["cache_read"] += u.get("cache_read_input_tokens", 0)
            usage["output"] += u.get("output_tokens", 0)
            for c in msg.get("content", []):
                if c.get("type") == "tool_use":
                    commands.append(c.get("input", {}).get("command") or c.get("input", {}).get("cmd"))
        elif ev.get("type") == "user":
            for c in msg.get("content", []):
                if c.get("type") == "tool_result":
                    content = c.get("content")
                    tool_chars += len(content if isinstance(content, str) else json.dumps(content))
        elif ev.get("type") == "result":
            answer = ev.get("result", "")
            turns = ev.get("num_turns", 0)
            if ev.get("is_error"):
                error = ev.get("error", "error")
    ans, correct = score(answer)
    return {
        "side": side, "idx": idx, "thread": thread, "wall_s": round(wall, 1), "turns": turns,
        "usage": usage, "context_tokens": usage["input"] + usage["cache_write"] + usage["cache_read"],
        "new_input_tokens": usage["input"] + usage["cache_write"],
        "tool_result_chars": tool_chars, "commands": commands, "answer": ans,
        "correct": correct, "of": len(TRUTH), "rc": p.returncode, "error": error,
    }


def save(results, name):
    with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
        json.dump({"truth": TRUTH, "prompt": PROMPT, "runs": results}, f, indent=2)


def main():
    results = []
    partial = os.path.join(HERE, "amp_results.partial.json")
    if os.environ.get("RESUME") and os.path.exists(partial):
        with open(partial, encoding="utf-8") as f:
            results = json.load(f)["runs"]
    done = {(r["side"], r["idx"]) for r in results}
    for i in range(RUNS):
        for side in ("on", "off") if i % 2 == 0 else ("off", "on"):
            if (side, i) in done:
                continue
            r = run_once(side, i)
            print(f"{side:3s} #{i} ctx={r['context_tokens']:>8} new_in={r['new_input_tokens']:>7} "
                  f"out={r['usage']['output']:>5} tool_chars={r['tool_result_chars']:>7} "
                  f"correct={r['correct']}/{r['of']} wall={r['wall_s']}s turns={r['turns']}"
                  f"{' ERROR: ' + r['error'] if r['error'] else ''}", flush=True)
            if r["error"]:
                save(results, "amp_results.partial.json")
                print("stopping: an aborted run would bias the comparison", flush=True)
                return 1
            results.append(r)
            save(results, "amp_results.partial.json")
    save(results, "amp_results.json")


if __name__ == "__main__":
    sys.exit(main())
