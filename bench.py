"""RTK benchmark: run each command raw vs via rtk, save outputs, measure timing,
then token-count every output with 5 LLM tokenizers.

Tokenizers:
  gpt4o   - OpenAI o200k_base (tiktoken)        -> GPT-4o / GPT-4.1 / o-series
  claude  - @anthropic-ai/tokenizer (npm)       -> Claude 3/4 family
  gemini  - Gemma-3 tokenizer.json (HF)         -> closest public proxy for Gemini
  llama   - Llama-3.1 tokenizer.json (HF)       -> Llama 3.1/3.2/3.3
  qwen    - Qwen3-8B tokenizer.json (HF)        -> Qwen family
"""
import json
import os
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.abspath(__file__))
HOME = os.environ["USERPROFILE"]
RTK = os.path.join(BASE, "rtk-bin", "rtk.exe")
REPO = os.path.join(BASE, "repo")
PY = os.path.join(BASE, "work", "pyproj")
RS = os.path.join(BASE, "work", "rsproj")
JS = os.path.join(BASE, "work", "jsproj")
VENV = os.path.join(BASE, ".venv", "Scripts")
TOKDIR = os.path.join(BASE, "tokenizers")
CLAUDE_TOK = os.path.join(BASE, "claude-tok")
NODE = r"C:\Program Files\nodejs\node.exe"
OUT = os.path.join(BASE, "out")

PATH_DIRS = [
    VENV,
    os.path.join(BASE, "rtk-bin"),
    r"C:\Program Files\Git\usr\bin",
    r"C:\Program Files\Git\cmd",
    r"C:\Program Files\nodejs",
    os.path.join(HOME, "AppData", "Roaming", "npm"),
    os.path.join(HOME, ".cargo", "bin"),
    r"C:\Windows\System32",
    r"C:\Windows",
]
# ripgrep has no standard install location on Windows; borrow it from the caller's PATH.
_rg = shutil.which("rg")
if _rg:
    PATH_DIRS.insert(0, os.path.dirname(_rg))
ENV = {
    "PATH": ";".join(PATH_DIRS),
    "SYSTEMROOT": r"C:\Windows",
    "SYSTEMDRIVE": "C:",
    "PATHEXT": ".COM;.EXE;.BAT;.CMD",
    "USERPROFILE": os.environ["USERPROFILE"],
    "HOMEDRIVE": os.environ.get("HOMEDRIVE", "C:"),
    "HOMEPATH": os.environ.get("HOMEPATH", ""),
    "TEMP": os.environ["TEMP"],
    "TMP": os.environ["TMP"],
    "NO_COLOR": "1",
    "APPDATA": os.environ.get("APPDATA", ""),
    "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", ""),
    "ProgramFiles": os.environ.get("ProgramFiles", r"C:\Program Files"),
    "ProgramFiles(x86)": os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
    "ProgramData": os.environ.get("ProgramData", r"C:\ProgramData"),
    "ComSpec": r"C:\Windows\System32\cmd.exe",
    "OS": "Windows_NT",
    "windir": r"C:\Windows",
    "NUMBER_OF_PROCESSORS": os.environ.get("NUMBER_OF_PROCESSORS", "8"),
    "PROCESSOR_ARCHITECTURE": os.environ.get("PROCESSOR_ARCHITECTURE", "AMD64"),
}

# id, cwd, reps, raw argv, rtk argv, description
COMMANDS = [
    ("git_status", REPO, 5, ["git", "status"], [RTK, "git", "status"],
     "git status - dirty tree (12 modified, 11 untracked, 2 staged)"),
    ("git_log", REPO, 5, ["git", "log", "-40"], [RTK, "git", "log", "-40"],
     "git log -40 - 40 commits with full messages"),
    ("git_log_oneline", REPO, 5, ["git", "log", "--oneline", "-40"],
     [RTK, "git", "log", "--oneline", "-40"],
     "git log --oneline -40 - already-compact input"),
    ("git_diff", REPO, 5, ["git", "diff", "HEAD~12"], [RTK, "git", "diff", "HEAD~12"],
     "git diff HEAD~12 - 12-commit patch (~170 KB)"),
    ("ls", REPO, 5, ["ls", "-la"], [RTK, "ls", "-la"],
     "ls -la - repo root, 45 entries"),
    ("rg", REPO, 5, ["rg", "-n", "pub fn", "src"], [RTK, "rg", "-n", "pub fn", "src"],
     "rg -n 'pub fn' src - 1300+ matches"),
    ("grep", REPO, 5, ["grep", "-rn", "unwrap()", "src"],
     [RTK, "grep", "-rn", "unwrap()", "src"],
     "grep -rn 'unwrap()' src - 1630 matches in 84 files"),
    ("cat_mid", REPO, 5, ["cat", "src/hooks/permissions.rs"],
     [RTK, "read", "--max-lines", "150", "src/hooks/permissions.rs"],
     "cat file (83 KB Rust) vs rtk read --max-lines 150"),
    ("cat_huge", REPO, 5, ["cat", "src/cmds/git/diff_cmd.rs"],
     [RTK, "read", "--max-lines", "150", "src/cmds/git/diff_cmd.rs"],
     "cat file (337 KB Rust) vs rtk read --max-lines 150"),
    ("pytest", PY, 3, ["python", "-m", "pytest"],
     [RTK, "test", "python", "-m", "pytest"],
     "pytest - 114 tests, 12 failures, 2 warnings"),
    ("cargo_test", RS, 3, ["cargo", "test"], [RTK, "cargo", "test"],
     "cargo test - 46 tests, 6 failures"),
    ("npm_test", JS, 3, ["npm.cmd", "test"], [RTK, "npm", "test"],
     "npm test (jest) - 36 tests, 5 failures"),
]


def resolve(argv):
    argv = list(argv)
    exe = shutil.which(argv[0], path=ENV["PATH"])
    if exe:
        argv[0] = exe
    return argv


def timed_run(argv, cwd):
    argv = resolve(argv)
    t0 = time.perf_counter()
    p = subprocess.run(argv, cwd=cwd, env=ENV, capture_output=True)
    dt = (time.perf_counter() - t0) * 1000.0
    return p.stdout, p.stderr, p.returncode, dt


def main():
    os.makedirs(OUT, exist_ok=True)
    results = {"commands": [], "meta": {
        "started": datetime.now(timezone.utc).isoformat(),
        "rtk_version": subprocess.run([RTK, "--version"], env=ENV, capture_output=True)
        .stdout.decode().strip(),
        "platform": os.environ.get("PROCESSOR_ARCHITECTURE", "") + " / " + sys.platform,
    }}

    # warm the test suites so cargo/jest caches are hot on both sides
    print("warming suites ...")
    timed_run(["cargo", "test"], RS)
    timed_run(["npm.cmd", "test"], JS)
    timed_run(["python", "-m", "pytest"], PY)

    for cid, cwd, reps, raw_argv, rtk_argv, desc in COMMANDS:
        print(f"running {cid} ...", flush=True)
        cdir = os.path.join(OUT, cid)
        os.makedirs(cdir, exist_ok=True)
        raw_ms, rtk_ms = [], []
        last = {}
        for rep in range(reps):
            ro, re_, rc, dms = timed_run(raw_argv, cwd)
            so, se, sc, dms2 = timed_run(rtk_argv, cwd)
            raw_ms.append(dms)
            rtk_ms.append(dms2)
            last = {"raw": (ro, re_, rc), "rtk": (so, se, sc)}
        for side, (o, e, rc) in last.items():
            with open(os.path.join(cdir, f"{side}.out.txt"), "wb") as f:
                f.write(o)
            with open(os.path.join(cdir, f"{side}.err.txt"), "wb") as f:
                f.write(e)
        entry = {
            "id": cid, "desc": desc, "reps": reps,
            "raw_argv": raw_argv[0] if len(raw_argv) == 1 else " ".join(raw_argv[:3]),
            "raw": {
                "out_bytes": len(last["raw"][0]), "err_bytes": len(last["raw"][1]),
                "comb_bytes": len(last["raw"][0]) + len(last["raw"][1]),
                "rc": last["raw"][2],
                "ms_median": round(statistics.median(raw_ms), 1),
                "ms_all": [round(m, 1) for m in raw_ms],
            },
            "rtk": {
                "out_bytes": len(last["rtk"][0]), "err_bytes": len(last["rtk"][1]),
                "comb_bytes": len(last["rtk"][0]) + len(last["rtk"][1]),
                "rc": last["rtk"][2],
                "ms_median": round(statistics.median(rtk_ms), 1),
                "ms_all": [round(m, 1) for m in rtk_ms],
            },
        }
        entry["bytes_saved_pct"] = round(
            100 * (1 - entry["rtk"]["comb_bytes"] / entry["raw"]["comb_bytes"]), 1)
        results["commands"].append(entry)

    # ---------------- token counting ----------------
    print("tokenizing ...", flush=True)
    import tiktoken
    from tokenizers import Tokenizer

    enc_o200k = tiktoken.get_encoding("o200k_base")
    hf_toks = {
        "gemini": Tokenizer.from_file(os.path.join(TOKDIR, "gemma3.json")),
        "llama": Tokenizer.from_file(os.path.join(TOKDIR, "llama31.json")),
        "qwen": Tokenizer.from_file(os.path.join(TOKDIR, "qwen3.json")),
    }

    def count(model, text):
        if model == "gpt4o":
            return len(enc_o200k.encode(text))
        return len(hf_toks[model].encode(text, add_special_tokens=False).ids)

    # build the claude manifest: one entry per side per command
    manifest = {}
    for cid, *_ in [(c[0],) for c in COMMANDS]:
        manifest[f"{cid}.raw"] = os.path.join(OUT, cid, "comb.raw.txt")
        manifest[f"{cid}.rtk"] = os.path.join(OUT, cid, "comb.rtk.txt")

    for cid, cwd, reps, raw_argv, rtk_argv, desc in COMMANDS:
        cdir = os.path.join(OUT, cid)
        for side in ("raw", "rtk"):
            with open(os.path.join(cdir, f"{side}.out.txt"), "rb") as f:
                out_txt = f.read().decode("utf-8", "replace")
            with open(os.path.join(cdir, f"{side}.err.txt"), "rb") as f:
                err_txt = f.read().decode("utf-8", "replace")
            with open(os.path.join(cdir, f"comb.{side}.txt"), "w", encoding="utf-8") as f:
                f.write(out_txt + err_txt)

    manifest_path = os.path.join(OUT, "claude_manifest.json")
    claude_out_path = os.path.join(OUT, "claude_counts.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f)
    p = subprocess.run([NODE, "count.js", manifest_path, claude_out_path],
                       cwd=CLAUDE_TOK, env=ENV, capture_output=True)
    print("claude counter:", p.stdout.decode().strip(), p.stderr.decode()[:200])
    with open(claude_out_path) as f:
        claude_counts = json.load(f)

    model_names = {
        "gpt4o": "GPT-4o (o200k_base)", "claude": "Claude (Anthropic tokenizer)",
        "gemini": "Gemini (Gemma-3 tokenizer)", "llama": "Llama 3.3 (Llama-3.1 tokenizer)",
        "qwen": "Qwen3 (Qwen3-8B tokenizer)",
    }
    totals = {m: {"raw": 0, "rtk": 0} for m in model_names}
    for entry in results["commands"]:
        cid = entry["id"]
        toks = {}
        for model in model_names:
            if model == "claude":
                raw_n = claude_counts[f"{cid}.raw"]
                rtk_n = claude_counts[f"{cid}.rtk"]
            else:
                with open(os.path.join(OUT, cid, "comb.raw.txt"), encoding="utf-8") as f:
                    raw_n = count(model, f.read())
                with open(os.path.join(OUT, cid, "comb.rtk.txt"), encoding="utf-8") as f:
                    rtk_n = count(model, f.read())
            toks[model] = {"raw": raw_n, "rtk": rtk_n,
                           "saved_pct": round(100 * (1 - rtk_n / raw_n), 1) if raw_n else 0.0}
            totals[model]["raw"] += raw_n
            totals[model]["rtk"] += rtk_n
        entry["tokens"] = toks
        entry["est_bytes_div4"] = {
            "raw": entry["raw"]["comb_bytes"] // 4,
            "rtk": entry["rtk"]["comb_bytes"] // 4,
        }

    results["totals"] = {
        m: {"raw": v["raw"], "rtk": v["rtk"],
            "saved_pct": round(100 * (1 - v["rtk"] / v["raw"]), 1)}
        for m, v in totals.items()
    }
    results["model_names"] = model_names
    raw_all = sum(e["raw"]["comb_bytes"] for e in results["commands"])
    rtk_all = sum(e["rtk"]["comb_bytes"] for e in results["commands"])
    results["bytes_total"] = {"raw": raw_all, "rtk": rtk_all,
                              "saved_pct": round(100 * (1 - rtk_all / raw_all), 1)}

    # rtk's own self-report (its tracking db logged all runs above)
    g = subprocess.run([RTK, "gain", "--all", "--format", "json"], env=ENV,
                       capture_output=True, cwd=os.environ["USERPROFILE"])
    results["rtk_gain_json"] = g.stdout.decode("utf-8", "replace")[:4000]
    g2 = subprocess.run([RTK, "gain"], env=ENV, capture_output=True,
                        cwd=os.environ["USERPROFILE"])
    results["rtk_gain_text"] = g2.stdout.decode("utf-8", "replace")[:4000]

    with open(os.path.join(BASE, "results.json"), "w") as f:
        json.dump(results, f, indent=2)
    print("\n=== totals (tokens) ===")
    for m, v in results["totals"].items():
        print(f"{m:8s} raw={v['raw']:>8} rtk={v['rtk']:>8} saved={v['saved_pct']}%")
    print(f"bytes   raw={raw_all} rtk={rtk_all} saved={results['bytes_total']['saved_pct']}%")


if __name__ == "__main__":
    main()
