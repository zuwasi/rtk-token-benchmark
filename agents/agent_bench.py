"""End-to-end A/B benchmark of rtk's official hooks in Claude Code and Factory Droid.

Same task, prompt and ground truth as amp/amp_bench.py. For the "on" side the agent gets
rtk's PreToolUse hook through a per-process --settings file (exactly what `rtk init` writes,
with rtk's absolute path); the "off" side runs with no extra settings. Global agent configs
are never touched. Runs alternate on/off. Results are saved after every run.

usage: python agent_bench.py claude|droid
"""
import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "amp"))
from amp_bench import PROMPT, REPO, TRUTH, score  # noqa: E402

RUNS = int(os.environ.get("RUNS_PER_SIDE", "3"))
RTK = shutil.which("rtk") or "rtk"

AGENTS = {
    # Droid runs hooks through cmd.exe without the user PATH on Windows, hence the absolute path.
    "claude": {"matcher": "Bash", "hook": f'"{RTK}" hook claude'},
    "droid": {"matcher": "Execute", "hook": f'"{RTK}" hook droid'},
}


def settings_file(agent):
    a = AGENTS[agent]
    path = os.path.join(HERE, "runs", f"{agent}_rtk_settings.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"hooks": {"PreToolUse": [{"matcher": a["matcher"], "hooks": [
            {"type": "command", "command": a["hook"]}]}]}}, f)
    return path


def command(agent, side):
    exe = shutil.which(agent) or agent
    extra = ["--settings", settings_file(agent)] if side == "on" else []
    if agent == "claude":
        # On Windows Claude Code also has a PowerShell tool, which rtk's hook (matcher "Bash")
        # never sees. It is disabled on both sides so the comparison measures rtk itself.
        return [exe, "-p", PROMPT, "--allowedTools", "Bash", "--disallowedTools", "PowerShell",
                "--output-format", "stream-json", "--verbose"] + extra
    # rtk leaves the permission decision to Droid, and Droid's medium autonomy does not
    # auto-approve the rewritten `rtk ...` commands, so both sides run at --auto high.
    return [exe, "exec", PROMPT, "--auto", "high", "-o", "stream-json"] + extra


def parse(agent, stdout):
    r = {"tool_chars": 0, "commands": [], "answer": "", "turns": 0, "model": None,
         "usage": {"input": 0, "cache_write": 0, "cache_read": 0, "output": 0}, "cost_usd": None,
         "credits": None, "error": None}
    for line in stdout.splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        t = ev.get("type")
        if agent == "claude":
            msg = ev.get("message") or {}
            if t == "assistant":
                r["model"] = msg.get("model", r["model"])
                for c in msg.get("content", []):
                    if c.get("type") == "tool_use":
                        r["commands"].append(c.get("input", {}).get("command"))
            elif t == "user":
                for c in msg.get("content", []):
                    if c.get("type") == "tool_result":
                        content = c.get("content")
                        r["tool_chars"] += len(content if isinstance(content, str) else json.dumps(content))
            elif t == "result":
                u = ev.get("usage") or {}
                r["usage"] = {"input": u.get("input_tokens", 0), "cache_write": u.get("cache_creation_input_tokens", 0),
                              "cache_read": u.get("cache_read_input_tokens", 0), "output": u.get("output_tokens", 0)}
                r["answer"], r["turns"], r["cost_usd"] = ev.get("result", ""), ev.get("num_turns", 0), ev.get("total_cost_usd")
                if ev.get("is_error"):
                    r["error"] = str(ev.get("result") or ev.get("subtype"))
        else:
            if t == "system":
                r["model"] = ev.get("model", r["model"])
            elif t == "tool_call":
                r["commands"].append((ev.get("parameters") or {}).get("command"))
            elif t == "tool_result":
                v = ev.get("value") if "value" in ev else ev.get("error")
                r["tool_chars"] += len(v if isinstance(v, str) else json.dumps(v))
            elif t == "completion":
                u = ev.get("usage") or {}
                r["usage"] = {"input": u.get("input_tokens", 0), "cache_write": u.get("cache_creation_input_tokens", 0),
                              "cache_read": u.get("cache_read_input_tokens", 0), "output": u.get("output_tokens", 0)}
                r["answer"], r["turns"], r["credits"] = ev.get("finalText", ""), ev.get("numTurns", 0), u.get("factory_credits")
            elif t == "error":
                r["error"] = str(ev.get("message") or ev)
    return r


def run_once(agent, side, idx):
    env = dict(os.environ, RTK_SUPPRESS_HOOK_WARNING="1")
    t0 = time.time()
    p = subprocess.run(command(agent, side), cwd=REPO, env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=1200)
    wall = time.time() - t0
    with open(os.path.join(HERE, "runs", f"{agent}_{side}_{idx}.jsonl"), "w", encoding="utf-8") as f:
        f.write(p.stdout)
    r = parse(agent, p.stdout)
    if not r["answer"] and not r["error"]:
        r["error"] = (p.stderr or "no answer")[-400:]
    ans, correct = score(r["answer"])
    u = r.pop("usage")
    return {"agent": agent, "side": side, "idx": idx, "wall_s": round(wall, 1), "usage": u,
            "context_tokens": u["input"] + u["cache_write"] + u["cache_read"],
            "new_input_tokens": u["input"] + u["cache_write"], "tool_result_chars": r.pop("tool_chars"),
            "answer": ans, "correct": correct, "of": len(TRUTH), "rc": p.returncode, **r}


def main(agent):
    out = os.path.join(HERE, f"{agent}_results.json")
    partial = out.replace(".json", ".partial.json")
    results = []
    if os.environ.get("RESUME") and os.path.exists(partial):
        with open(partial, encoding="utf-8") as f:
            results = json.load(f)["runs"]
    done = {(r["side"], r["idx"]) for r in results}

    def save(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"agent": agent, "truth": TRUTH, "runs": results}, f, indent=2)

    for i in range(RUNS):
        for side in ("on", "off") if i % 2 == 0 else ("off", "on"):
            if (side, i) in done:
                continue
            r = run_once(agent, side, i)
            print(f"{agent} {side:3s} #{i} ctx={r['context_tokens']:>8} new_in={r['new_input_tokens']:>7} "
                  f"out={r['usage']['output']:>5} tool_chars={r['tool_result_chars']:>7} correct={r['correct']}/{r['of']} "
                  f"wall={r['wall_s']}s turns={r['turns']} model={r['model']}"
                  f"{' ERROR: ' + r['error'] if r['error'] else ''}", flush=True)
            if r["error"]:
                save(partial)
                return 1
            results.append(r)
            save(partial)
    save(out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
