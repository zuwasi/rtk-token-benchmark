"""Build presentation.html (self-contained) from results.json, captured outputs and assets."""
import base64
import html
import json
import re
import os
import statistics

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "out")
REPO_URL = "https://github.com/zuwasi/rtk-token-benchmark"

with open(os.path.join(BASE, "results.json"), encoding="utf-8") as f:
    R = json.load(f)


def b64(path, mime):
    with open(os.path.join(BASE, path), "rb") as f:
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode()


def read_out(cid, name, limit=None):
    with open(os.path.join(OUT, cid, name), "rb") as f:
        txt = f.read().decode("utf-8", "replace").replace("\r\n", "\n")
    return txt[:limit] if limit else txt


MODEL_ORDER = ["gpt4o", "claude", "gemini", "llama", "qwen"]
MODEL_LABEL = {"gpt4o": "GPT-4o", "claude": "Claude", "gemini": "Gemini",
               "llama": "Llama 3.3", "qwen": "Qwen3"}
MODEL_TOK = {"gpt4o": "o200k_base via tiktoken", "claude": "@anthropic-ai/tokenizer (npm)",
             "gemini": "Gemma-3 tokenizer.json (stand-in)", "llama": "Llama-3.1 tokenizer.json",
             "qwen": "Qwen3-8B tokenizer.json"}
MODEL_COLOR = {"gpt4o": "#10a37f", "claude": "#c96442", "gemini": "#3d7cdb",
               "llama": "#7a5af5", "qwen": "#d63384"}
PRICE = {"gpt4o": (2.50, "GPT-4o, OpenAI list"), "claude": (3.00, "Sonnet 4.5, Anthropic list"),
         "gemini": (0.15, "2.5 Flash, Google list"), "llama": (0.59, "3.3 70B, Groq list"),
         "qwen": (0.40, "Plus tier, Alibaba list")}

CMD_INFO = {
    "git_status": ("git status", "rtk git status", "Dirty tree: 12 modified, 11 untracked, 2 staged"),
    "git_log": ("git log -40", "rtk git log -40", "40 commits with full messages"),
    "git_log_oneline": ("git log --oneline -40", "rtk git log --oneline -40", "Output that is already compact"),
    "git_diff": ("git diff HEAD~12", "rtk git diff HEAD~12", "12-commit patch, about 170 KB"),
    "ls": ("ls -la", "rtk ls -la", "Repo root, 45 entries"),
    "rg": ("rg -n 'pub fn' src", "rtk rg -n 'pub fn' src", "1,300+ matches across the codebase"),
    "grep": ("grep -rn 'unwrap()' src", "rtk grep -rn 'unwrap()' src", "1,630 matches in 84 files"),
    "cat_mid": ("cat permissions.rs", "rtk read --max-lines 150", "83 KB Rust source file"),
    "cat_huge": ("cat diff_cmd.rs", "rtk read --max-lines 150", "337 KB Rust source file"),
    "pytest": ("python -m pytest", "rtk test python -m pytest", "114 tests, 12 failing, 2 warnings"),
    "cargo_test": ("cargo test", "rtk cargo test", "46 tests, 6 failing"),
    "npm_test": ("npm test (jest)", "rtk npm test", "36 tests, 5 failing"),
}

commands = []
for c in R["commands"]:
    raw_cmd, rtk_cmd, scen = CMD_INFO[c["id"]]
    commands.append({
        "id": c["id"], "raw": raw_cmd, "rtkCmd": rtk_cmd, "scen": scen,
        "rawBytes": c["raw"]["comb_bytes"], "rtkBytes": c["rtk"]["comb_bytes"],
        "savedPct": c["bytes_saved_pct"], "rcRaw": c["raw"]["rc"], "rcRtk": c["rtk"]["rc"],
        "msRaw": c["raw"]["ms_median"], "msRtk": c["rtk"]["ms_median"], "reps": c["reps"],
        "tokens": {m: c["tokens"][m] for m in MODEL_ORDER}, "estDiv4": c["est_bytes_div4"],
    })

totals = {m: R["totals"][m] for m in MODEL_ORDER}
DATA = {
    "repoUrl": REPO_URL,
    "logo": b64("assets/esl-logo.png", "image/png"),
    "photo": b64("assets/daniel-liezrowice.jpg", "image/jpeg"),
    "rtkVersion": R["meta"]["rtk_version"].replace("rtk ", ""),
    "M": MODEL_ORDER, "label": MODEL_LABEL, "tok": MODEL_TOK, "color": MODEL_COLOR,
    "price": {m: {"p": PRICE[m][0], "src": PRICE[m][1]} for m in MODEL_ORDER},
    "totals": totals,
    "meanSaved": round(statistics.mean(t["saved_pct"] for t in totals.values()), 1),
    "bytesTotal": R["bytes_total"],
    "commands": commands,
    "snip": {
        "statusRaw": read_out("git_status", "raw.out.txt"),
        "statusRtk": read_out("git_status", "rtk.out.txt"),
        "pytestRaw": read_out("pytest", "comb.raw.txt", 3200),
        "pytestRtk": read_out("pytest", "comb.rtk.txt"),
        "rgRtk": read_out("rg", "rtk.out.txt", 900),
        "catRtk": read_out("cat_mid", "rtk.out.txt", 1400),
        "onelineRaw": "\n".join(read_out("git_log_oneline", "raw.out.txt").splitlines()[:9]),
        "onelineRtk": "\n".join(read_out("git_log_oneline", "rtk.out.txt").splitlines()[:9]),
        "jestRtk": "\n".join(read_out("npm_test", "comb.rtk.txt").splitlines()[:14]),
    },
    "gainText": R["rtk_gain_text"].strip(),
}


def load_amp():
    path = os.path.join(BASE, "amp", "amp_results.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        runs = json.load(f)["runs"]

    def side(s):
        rs = [r for r in runs if r["side"] == s]
        mean = lambda f: statistics.mean(f(r) for r in rs)
        return {
            "chars": mean(lambda r: r["tool_result_chars"]),
            "ctx": mean(lambda r: r["context_tokens"]),
            "newIn": mean(lambda r: r["new_input_tokens"]),
            "cacheRead": mean(lambda r: r["usage"]["cache_read"]),
            "out": mean(lambda r: r["usage"]["output"]),
            "wall": mean(lambda r: r["wall_s"]),
            "correct": round(mean(lambda r: r["correct"]), 1),
            "correctAll": " · ".join(str(r["correct"]) for r in rs),
        }

    on, off = side("on"), side("off")
    d = {k: round(100 * (on[k] / off[k] - 1), 1) for k in ("chars", "ctx", "newIn", "cacheRead", "out", "wall")}
    with open(os.path.join(BASE, "amp", "amp_note.txt"), encoding="utf-8") as f:
        note = f.read().strip()
    return {"n": len([r for r in runs if r["side"] == "on"]), "on": on, "off": off, "d": d,
            "runs": runs, "note": note}


def plugin_excerpt():
    with open(os.path.join(BASE, "amp", "rtk.ts"), encoding="utf-8") as f:
        src = f.read()
    a = src.index("amp.on('tool.call'")
    b = src.index("amp.registerCommand")
    body = [ln for ln in src[a:b].rstrip().splitlines() if not ln.strip().startswith("//")]
    code = html.escape("\n".join(body))
    code = re.sub(r"(//[^\n]*)", r'<span class="c">\1</span>', code)
    code = re.sub(r"\b(const|let|return|if|await|async|try|catch)\b", r'<span class="k">\1</span>', code)
    return code, src.count("\n") + 1


def load_agents():
    files = {"amp": "amp/amp_results.json", "amp_wsl": "amp/amp_results_wsl.json",
             "claude": "agents/claude_results.json", "droid": "agents/droid_results.json"}
    info = {
        "amp": ("Amp · Windows", "Custom plugin (tool.call → modify)", "Cuts each result at 50K chars", None),
        "amp_wsl": ("Amp · WSL Ubuntu", "Same plugin, Linux rtk build, 2nd account", "Cuts each result at 50K chars", None),
        "claude": ("Claude Code", "Official PreToolUse hook, Bash tool", "Saves large outputs to a file, 2 KB preview", "cost_usd"),
        "droid": ("Droid", "Official PreToolUse hook, Execute tool", "Keeps ~10K chars, rest to a log file", "credits"),
    }
    out = []
    for key, rel in files.items():
        path = os.path.join(BASE, rel)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8") as f:
            doc = json.load(f)
        runs, truth = doc["runs"], doc["truth"]

        def mean(side, fn):
            return statistics.mean(fn(r) for r in runs if r["side"] == side)

        def delta(fn):
            return round(100 * (mean("on", fn) / mean("off", fn) - 1), 1)

        name, hook, cap, cost_key = info[key]
        metrics = {"chars": lambda r: r["tool_result_chars"], "ctx": lambda r: r["context_tokens"],
                   "out": lambda r: r["usage"]["output"], "wall": lambda r: r["wall_s"]}
        if cost_key:
            metrics["cost"] = lambda r: r[cost_key]
        per_cmd = []
        for cmd in AGENT_CMDS:
            row = {"cmd": cmd}
            for side in ("off", "on"):
                xs = [pc for r in runs if r["side"] == side for pc in r.get("per_command", []) if pc["cmd"] == cmd]
                row[side] = statistics.median(x["chars"] for x in xs) if xs else None
                row[side + "Note"] = next((x["note"] for x in xs if x["note"]), "")
            per_cmd.append(row)

        def answer(r):
            a = r.get("answer")
            if isinstance(a, str):
                m = re.search(r"\{.*\}", a, re.S)
                a = json.loads(m.group(0)) if m else {}
            return a or {}

        def wrong(r, q):
            return str(answer(r).get(q)).lower() != str(truth[q]).lower()

        row = {"key": key, "name": name, "hook": hook, "cap": cap,
               "model": next((r.get("model") for r in runs if r.get("model")), None),
               "n": len([r for r in runs if r["side"] == "on"]),
               "chars": delta(metrics["chars"]), "ctx": delta(metrics["ctx"]),
               "offOk": [r["correct"] for r in runs if r["side"] == "off"],
               "onOk": [r["correct"] for r in runs if r["side"] == "on"],
               "cost": delta(metrics["cost"]) if cost_key else None,
               "costUnit": {"cost_usd": "USD", "credits": "Factory credits"}.get(cost_key),
               "m": {k: {"off": mean("off", f), "on": mean("on", f), "d": delta(f)} for k, f in metrics.items()},
               "perCmd": per_cmd,
               "miss": {q: {s: sum(wrong(r, q) for r in runs if r["side"] == s) for s in ("off", "on")} for q in truth},
               "runs": [{"side": r["side"], "idx": r["idx"], "chars": r["tool_result_chars"], "ctx": r["context_tokens"],
                         "correct": r["correct"], "wall": r["wall_s"], "cost": r.get(cost_key) if cost_key else None}
                        for r in sorted(runs, key=lambda r: (r["idx"], r["side"] != "off"))]}
        out.append(row)
    return out or None


AGENT_CMDS = ["git status", "git log -40", "git diff HEAD~12", 'rg -n "pub fn" src', "cargo test"]


DATA["agents"] = load_agents()
DATA["amp"] = load_amp()
DATA["ampPluginCode"], DATA["ampPluginLines"] = plugin_excerpt()
DATA["ampVersion"] = "0.0.1791950451"

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>rtk token-savings benchmark | Daniel Liezrowice, Engineering Software Lab</title>
<style>
__CSS__
</style>
</head>
<body>
<div id="stage"></div>
<button id="home" title="First slide (Home)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h5v-6h4v6h5V10"/></svg>home</button>
<div id="pos"></div>
<button class="navbtn" id="prev" title="Previous (Left arrow)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><path d="M15 4l-8 8 8 8"/></svg></button>
<button class="navbtn" id="next" title="Next (Right arrow)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6"><path d="M9 4l8 8-8 8"/></svg></button>
<div id="track"><i></i></div>
<script>
const D = __DATA_JSON__;
const M = D.M;
const fmtK = n => n >= 1e6 ? (n/1e6).toFixed(2)+"M" : n >= 1000 ? (n/1000).toFixed(1)+"K" : ""+Math.round(n);
const fmtB = n => n >= 1e6 ? (n/1e6).toFixed(2)+" MB" : n >= 1000 ? (n/1000).toFixed(1)+" KB" : n+" B";
const esc = s => s.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
const C = id => D.commands.find(c => c.id === id);
const pctColor = p => p >= 80 ? "#1f8a5b" : p >= 50 ? "#3d7cdb" : p >= 20 ? "#e09b00" : "#c2410c";
const LINKEDIN = "https://www.linkedin.com/in/liezrowice/";
const ESL = "https://eswlab.com";
const slides = [];

function frame(sec, title, body, note) {
  slides.push({sec, html: `
  <div class="hd"><div><div class="sec"><b>${String(slides.length+1).padStart(2,"0")}</b>${sec}</div><h2>${title}</h2></div>
    <a class="logo" href="${ESL}" target="_blank" title="Engineering Software Lab"><img src="${D.logo}" alt="ESL"></a></div>
  <div class="rule"></div>
  <div class="body">${body}</div>
  <div class="ft"><div class="who"><img src="${D.photo}" alt="">Benchmark by
    <a href="${LINKEDIN}" target="_blank">Daniel Liezrowice</a> · Engineering Software Lab · <a href="${ESL}" target="_blank">eswlab.com</a></div>
    <div>${note ? note + " · " : ""}__PAGE__</div></div>`});
}

function hbar(items, o) {
  const W = o.w, rowH = o.rowH, L = o.padL, Rr = o.padR, top = 6, H = items.length * rowH + top + 30;
  const max = o.max || Math.max(...items.map(i => Math.max(i.v, i.v2 || 0)));
  const x = v => L + v / max * (W - L - Rr);
  const fs = o.fs || 20, mono = 'font-family="Cascadia Mono,Consolas,monospace"';
  let s = `<svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">`;
  [0, .25, .5, .75, 1].map(f => f * max).forEach(v => {
    s += `<line x1="${x(v)}" y1="${top}" x2="${x(v)}" y2="${H-26}" stroke="${v===0?'#1c2430':'#e3e8ee'}" stroke-width="1"/>`;
    s += `<text x="${x(v)}" y="${H-8}" text-anchor="middle" font-size="13" fill="#8a95a5" ${mono}>${o.tickFmt ? o.tickFmt(v) : fmtK(v)}</text>`;
  });
  items.forEach((it, i) => {
    const cy = top + i * rowH + rowH / 2;
    s += `<text x="${L-14}" y="${cy+6}" text-anchor="end" font-size="${fs}" font-weight="600" fill="#1c2430" ${it.mono?mono:''}>${it.l}</text>`;
    if (it.v2 !== undefined) {
      s += `<rect x="${L}" y="${cy-15}" width="${x(it.v)-L}" height="13" fill="#b8c1cc"/>`;
      s += `<rect x="${L}" y="${cy+2}" width="${Math.max(2,x(it.v2)-L)}" height="13" fill="${it.c}"/>`;
    } else {
      s += `<rect x="${L}" y="${cy-11}" width="${Math.max(2,x(it.v)-L)}" height="22" fill="${it.c}"/>`;
    }
    s += `<text x="${x(Math.max(it.v,it.v2||0))+10}" y="${cy+6}" font-size="${fs-3}" fill="#566273" ${mono}>${it.n}</text>`;
  });
  return s + `</svg>`;
}

const T = D.totals, mean = D.meanSaved;
M.forEach(m => { T[m].saved_pct = T[m].saved_pct.toFixed(1); });
const minS = Math.min(...M.map(m => +T[m].saved_pct)).toFixed(1), maxS = Math.max(...M.map(m => +T[m].saved_pct)).toFixed(1);
const ratio = (D.bytesTotal.raw / D.bytesTotal.rtk).toFixed(1);

// 1 ─ title
slides.push({sec: "Title", html: `
<div style="position:absolute;inset:0;display:flex">
  <div style="flex:1.3;padding:70px 64px 60px 80px;display:flex;flex-direction:column">
    <a href="${ESL}" target="_blank"><img src="${D.logo}" style="height:78px" alt="ESL, Engineering Software Lab"></a>
    <div class="mono" style="margin-top:58px;font-size:16px;letter-spacing:2px;color:var(--blue);text-transform:uppercase">Technical report · ESL-TR-2026-10 · October 2026</div>
    <h1 style="font-size:58px;font-weight:600;line-height:1.1;letter-spacing:-1px;margin-top:16px">rtk output compression:<br>five LLM tokenizers,<br>three coding agents</h1>
    <div style="height:1px;background:var(--ink);margin:30px 0 24px;width:100%"></div>
    <p class="lead" style="font-size:21px;max-width:820px">12 developer commands run with and without rtk v${D.rtkVersion}; outputs counted with
      the GPT-4o, Claude, Gemma, Llama and Qwen tokenizers. Then the same rtk tested end to end inside three coding agents:
      Claude Code and Droid through rtk's official hooks, and Amp through a plugin written for this study.</p>
    <div style="margin-top:auto;display:flex;align-items:center;gap:20px">
      <img src="${D.photo}" style="width:92px;height:92px;border-radius:2px;object-fit:cover;border:1px solid var(--line)" alt="Daniel Liezrowice">
      <div><div style="font-size:24px;font-weight:600">Daniel Liezrowice</div>
        <div style="font-size:18px;color:var(--muted);margin:3px 0 6px">Engineering Software Lab (ESL)</div>
        <div class="mono" style="font-size:15px"><a href="${LINKEDIN}" target="_blank">linkedin.com/in/liezrowice</a> · <a href="${ESL}" target="_blank">eswlab.com</a>
        · <a href="${D.repoUrl}" target="_blank">github.com/zuwasi/rtk-token-benchmark</a></div></div>
    </div>
  </div>
  <div class="grid-bg" style="flex:1;border-left:1px solid var(--line);padding:84px 56px 60px;display:flex;flex-direction:column;gap:22px">
    <div class="card" style="padding:18px 22px">
      <h4>Table 1 · Tokens in command output</h4>
      <table class="tight">
        <tr><th>Tokenizer</th><th class="n">Raw</th><th class="n">rtk</th><th class="n">Δ</th></tr>
        ${M.map(m => `<tr><td><span class="dot" style="background:${D.color[m]}"></span>${D.label[m]}</td>
          <td class="n">${fmtK(T[m].raw)}</td><td class="n">${fmtK(T[m].rtk)}</td><td class="n"><b class="g">−${T[m].saved_pct}%</b></td></tr>`).join("")}
      </table>
      <div class="fig">Sum of 12 command outputs · ${fmtB(D.bytesTotal.raw)} → ${fmtB(D.bytesTotal.rtk)}</div>
    </div>
    ${D.amp ? "" : `<div class="card edge" style="padding:18px 22px">
      <h4>Key findings</h4>
      <ol class="num" style="margin:0">
        <li style="font-size:17px;margin-bottom:8px">${minS}–${maxS}% fewer tokens with all five tokenizers.</li>
        <li style="font-size:17px;margin-bottom:8px">Exit codes preserved on 12 of 12 commands.</li>
        <li style="font-size:17px;margin-bottom:8px">Overhead of 8–146 ms per command.</li>
        <li style="font-size:17px;margin-bottom:0">Amp plugin rewrites shell calls transparently (slide 16).</li>
      </ol>
    </div>`}
    ${D.agents ? `<div class="card" style="padding:18px 22px">
      <h4>Table 2 · Inside coding agents, rtk on vs off</h4>
      <table class="tight">
        <tr><th>Agent</th><th class="n">Tool output</th><th class="n">Context</th><th class="n">Correct of 7</th></tr>
        ${D.agents.map(a => `<tr><td>${a.name}</td><td class="n"><b class="${a.chars<0?'g':'r'}">${a.chars>0?'+':''}${a.chars.toFixed(0)}%</b></td>
          <td class="n"><b class="${a.ctx<0?'g':'r'}">${a.ctx>0?'+':''}${a.ctx.toFixed(0)}%</b></td>
          <td class="n">${(a.offOk.reduce((x,y)=>x+y,0)/a.offOk.length).toFixed(1)} → <b class="g">${(a.onOk.reduce((x,y)=>x+y,0)/a.onOk.length).toFixed(1)}</b></td></tr>`).join("")}
      </table>
      <div class="fig">Same task in each agent · mean of ${D.agents[0].n} threads per side</div></div>` : ""}
  </div>
</div>`});

// 2 ─ about
frame("About this study", "Who ran it, and what question it answers", `
<div class="row">
  <div class="col" style="flex:.8">
    <div class="card" style="text-align:center;padding:34px 26px">
      <img src="${D.photo}" style="width:210px;height:210px;border-radius:2px;object-fit:cover;border:1px solid var(--line)" alt="Daniel Liezrowice">
      <div style="font-size:30px;font-weight:700;margin-top:18px">Daniel Liezrowice</div>
      <div style="font-size:20px;color:var(--muted);margin-top:4px">Engineering Software Lab (ESL)</div>
      <div style="font-size:19px;margin-top:16px;line-height:1.8"><a href="${LINKEDIN}" target="_blank">linkedin.com/in/liezrowice</a><br>
        <a href="${ESL}" target="_blank">eswlab.com</a></div>
    </div>
    <div class="card amber grow"><h4>Open data</h4><p class="small" style="font-size:18px">Scripts, raw command outputs, token counts and this deck
      are published under the MIT licence at<br><a href="${D.repoUrl}" target="_blank">${D.repoUrl.replace("https://","")}</a></p></div>
  </div>
  <div class="col">
    <div class="card edge"><h4>The question</h4><p>rtk promises to cut the tokens your coding agent spends on shell output by 60–90%.
      Does that hold up on real commands, does it depend on the LLM, and what happens inside Claude Code, Droid and Amp?</p></div>
    <div class="card edge"><h4>What I did</h4><p>I designed and ran this benchmark myself on a Windows 11 workstation.
      rtk was tested exactly as shipped in its public v${D.rtkVersion} release, with no configuration changes. Each command ran
      with and without rtk; every output was counted with five different tokenizers.</p></div>
    <div class="card edge grow"><h4>Two levels of test</h4><p style="font-size:19px"><b>Commands (slides 5–15):</b> what rtk removes from
      12 outputs, counted with five tokenizers. <b>Agents (slides 16–22):</b> the same task run in Claude Code, Droid and Amp with rtk on
      and off, scoring tokens and answer accuracy. rtk is compared with no tool, not with other compressors, and none of this is a bill forecast.</p></div>
  </div>
</div>`);

// 3 ─ what is rtk
frame("Background", "What rtk does", `
<div style="display:flex;flex-direction:column;gap:26px;height:100%">
  <div class="flow">
    <div class="nd">Coding agent runs<br><span class="mono">git status</span></div><div class="ar">→</div>
    <div class="nd hl">rtk hook rewrites it to<br><span class="mono">rtk git status</span></div><div class="ar">→</div>
    <div class="nd">Real git runs,<br>full output</div><div class="ar">→</div>
    <div class="nd hl">rtk filters<br>the output</div><div class="ar">→</div>
    <div class="nd">Agent reads the<br>short version</div>
  </div>
  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:20px">
    <div class="card edge"><h4>Filter</h4><p class="small" style="font-size:18px">Drops progress lines, boilerplate hints, blank padding and passing-test noise.</p></div>
    <div class="card edge"><h4>Group</h4><p class="small" style="font-size:18px">Collects grep matches by file and lint errors by rule instead of repeating paths.</p></div>
    <div class="card edge"><h4>Truncate</h4><p class="small" style="font-size:18px">Keeps the useful head, and stores the rest behind an <span class="mono">rtk recall &lt;id&gt;</span> handle.</p></div>
    <div class="card edge"><h4>Deduplicate</h4><p class="small" style="font-size:18px">Collapses repeated log lines into a single line with a count.</p></div>
  </div>
  <div class="card grow">
    <table>
      <tr><th style="width:38%">What the project claims</th><th>How I checked it</th><th class="n">Slide</th></tr>
      <tr><td>"60–90% fewer tokens on common dev commands"</td><td>12 commands, real tokenizers for 5 model families</td><td class="n">6–12</td></tr>
      <tr><td>"&lt;10 ms overhead"</td><td>Median wall-clock time, 3–5 runs per side</td><td class="n">13</td></tr>
      <tr><td>Exit codes and failures are preserved</td><td>Compared exit codes and failure lists side by side</td><td class="n">9, 11</td></tr>
      <tr><td>Supports your agent</td><td>Official hooks in Claude Code and Droid; built an Amp plugin; A/B in all three</td><td class="n">16–22</td></tr>
    </table>
  </div>
</div>`);

// 4 ─ setup
frame("Method", "Test setup", `
<div class="row">
  <div class="col">
    <div class="card"><h4>Environment</h4><table class="tight">
      <tr><td>rtk</td><td>v${D.rtkVersion}, official Windows x64 release</td></tr>
      <tr><td>Repository</td><td>rtk-ai/rtk, develop @ f16beca (798 files)</td></tr>
      <tr><td>Machine</td><td>Windows 11 · Python 3.14 · Git 2.56 · Node 22 · Cargo 1.97</td></tr>
      <tr><td>Test suites</td><td>Generated pytest, cargo and jest projects with deliberate failures</td></tr>
    </table></div>
    <div class="card grow"><h4>Measurement rules</h4><ol class="num">
      <li>Same command, same directory, run raw and then through rtk.</li>
      <li>stdout and stderr counted together, because the agent sees both.</li>
      <li>3–5 runs per side; timing is the median, tokens come from the final run.</li>
      <li>No special tokens added; files decoded as UTF-8.</li></ol></div>
  </div>
  <div class="col">
    <div class="card"><h4>Five tokenizers</h4><table class="tight">
      ${M.map(m => `<tr><td style="white-space:nowrap"><span class="dot" style="background:${D.color[m]}"></span><b>${D.label[m]}</b></td><td>${D.tok[m]}</td></tr>`).join("")}
    </table></div>
    <div class="card amber grow"><h4>Two judgement calls</h4>
      <p class="small" style="font-size:18px;margin-bottom:10px"><b style="color:var(--ink)">Gemini:</b> Google publishes no Gemini tokenizer.
        Gemma-3, its open sibling, is the closest public stand-in.</p>
      <p class="small" style="font-size:18px"><b style="color:var(--ink)">File reads:</b> <span class="mono">rtk read</span> passes files through
        unchanged by default. I used <span class="mono">--max-lines 150</span>, the structural preview that matches rtk's documented
        "signatures and structure" behaviour.</p></div>
  </div>
</div>`);

// 5 ─ commands
frame("Method", "The 12 commands", `
<div class="card" style="padding:12px 20px">
<table class="tight">
  <tr><th>Without rtk</th><th>With rtk</th><th>Scenario</th><th class="n">Raw output</th><th class="n">Exit code</th></tr>
  ${D.commands.map(c => `<tr><td class="mono" style="font-size:16px">${c.raw}</td><td class="mono" style="font-size:16px;color:var(--blue)">${c.rtkCmd}</td>
    <td style="font-size:17px">${c.scen}</td><td class="n">${fmtB(c.rawBytes)}</td><td class="n">${c.rcRaw} / ${c.rcRtk}</td></tr>`).join("")}
</table></div>`, "exit codes shown as raw / rtk");

// 6 ─ headline
frame("Result", `${minS}–${maxS}% fewer tokens, whichever model you use`, `
<div style="display:flex;flex-direction:column;height:100%;gap:22px">
  <div class="card" style="padding:22px 26px">
    <div class="lab">Total tokens across all 12 outputs <span><span class="dot" style="background:#d5dbe3"></span>without rtk &nbsp; <span class="dot" style="background:var(--blue)"></span>with rtk</span></div>
    ${hbar(M.map(m => ({l: D.label[m], v: T[m].raw, v2: T[m].rtk, c: D.color[m],
      n: `${fmtK(T[m].raw)} → ${fmtK(T[m].rtk)}  (−${T[m].saved_pct}%)`})), {w: 1400, rowH: 62, padL: 150, padR: 330, fs: 22})}
  </div>
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:22px;flex:1">
    <div class="card edge"><div class="stat" style="color:var(--good)">${mean}%</div><div class="stat-l">average token reduction across the five tokenizers</div></div>
    <div class="card edge"><div class="stat" style="font-size:42px;white-space:nowrap">${fmtB(D.bytesTotal.raw)} → ${fmtB(D.bytesTotal.rtk)}</div><div class="stat-l">bytes delivered to the context window (−${D.bytesTotal.saved_pct}%)</div></div>
    <div class="card edge"><div class="stat">${ratio}×</div><div class="stat-l">less output for the same 12 commands</div></div>
  </div>
</div>`);

// 7 ─ by command
{
  const s = [...D.commands].sort((a, b) => b.savedPct - a.savedPct);
  const band = (lo, hi) => s.filter(c => c.savedPct >= lo && c.savedPct < hi).length;
  frame("Result", "Savings by command", `
<div class="row">
  <div class="card" style="flex:2.3;padding:16px 20px">
    ${hbar(s.map(c => ({l: c.id, mono: true, v: c.savedPct, c: pctColor(c.savedPct),
      n: `${c.savedPct}%   ${fmtB(c.rawBytes)} → ${fmtB(c.rtkBytes)}`})), {w: 980, rowH: 48, padL: 190, padR: 290, max: 100, fs: 18, tickFmt: v => v + "%"})}
  </div>
  <div class="col">
    <div class="card"><h4>Distribution</h4><table class="tight">
      <tr><td><span class="dot" style="background:#1f8a5b"></span>80% or more</td><td class="n"><b>${band(80,101)}</b> commands</td></tr>
      <tr><td><span class="dot" style="background:#3d7cdb"></span>50–80%</td><td class="n"><b>${band(50,80)}</b> commands</td></tr>
      <tr><td><span class="dot" style="background:#e09b00"></span>20–50%</td><td class="n"><b>${band(20,50)}</b> command</td></tr>
      <tr><td><span class="dot" style="background:#c2410c"></span>under 20%</td><td class="n"><b>${band(0,20)}</b> commands</td></tr></table></div>
    <div class="card edge grow"><h4>The pattern</h4><p style="font-size:19px">The bigger and noisier the raw output, the more rtk removes.
      Whole-file reads, huge greps and long diffs lose 85–99%. Output that is already terse, such as
      <span class="mono">--oneline</span> logs and jest's failure summary, passes through almost untouched.</p>
      <p class="small" style="margin-top:12px">Byte savings shown. Token savings land within 1.5 points of these for every tokenizer.</p></div>
  </div>
</div>`);
}

// 8 ─ git status
{
  const c = C("git_status");
  frame("Before and after", "git status: same information, 40% less text", `
<div class="row">
  <div class="col"><div class="lab">Without rtk <span>${fmtB(c.rawBytes)} · ${c.tokens.gpt4o.raw} GPT-4o tokens</span></div>
    <pre class="snip raw grow">${esc(D.snip.statusRaw)}</pre></div>
  <div class="col"><div class="lab">With rtk <span>${fmtB(c.rtkBytes)} · ${c.tokens.gpt4o.rtk} GPT-4o tokens</span></div>
    <pre class="snip rtk" style="flex:0 0 auto;font-size:12.5px">${esc(D.snip.statusRtk)}</pre>
    <div class="card edge" style="padding:16px 22px"><h4 style="margin-bottom:6px">What was removed</h4><p style="font-size:17px">The git add / restore hints,
      section headings and indentation. Each file keeps its status code (<span class="mono">M</span>, <span class="mono">??</span>),
      so staged, modified and untracked files are still clear.</p></div></div>
</div>`);
}

// 9 ─ pytest
{
  const c = C("pytest");
  frame("Before and after", `pytest: ${fmtB(c.rawBytes)} of output becomes ${fmtB(c.rtkBytes)}`, `
<div class="row">
  <div class="col" style="flex:1.1"><div class="lab">Without rtk, first part only <span>${fmtB(c.rawBytes)} total</span></div>
    <pre class="snip raw grow" style="font-size:13.5px">${esc(D.snip.pytestRaw)}</pre></div>
  <div class="col"><div class="lab">With rtk, complete output <span>${fmtB(c.rtkBytes)}</span></div>
    <pre class="snip rtk" style="flex:0 0 auto;font-size:13.5px">${esc(D.snip.pytestRtk)}</pre>
    <div class="card edge grow"><h4>What survives, what goes</h4><p style="font-size:19px">The first 10 failures are named with their error; the
      last 2 are counted as "+2 more failures". The exit code stays 1. Passing tests, progress dots and full tracebacks are dropped.
      The agent knows what broke, for ${c.savedPct}% fewer bytes, but would need a rerun to see the two hidden failures.</p></div></div>
</div>`);
}

// 10 ─ biggest wins
{
  const wins = [...D.commands].sort((a, b) => b.savedPct - a.savedPct).slice(0, 6);
  frame("Where rtk helps most", "Large outputs give the largest savings", `
<div style="display:flex;flex-direction:column;gap:22px;height:100%">
  <div class="card" style="padding:12px 20px"><table class="tight">
    <tr><th>Command</th><th>Scenario</th><th class="n">Raw → with rtk</th><th class="n">Saved</th><th class="n">GPT-4o tokens</th><th class="n">Claude tokens</th></tr>
    ${wins.map(c => `<tr><td class="mono" style="font-size:16px">${c.raw}</td><td style="font-size:17px">${c.scen}</td>
      <td class="n">${fmtB(c.rawBytes)} → <b>${fmtB(c.rtkBytes)}</b></td><td class="n"><b class="g">${c.savedPct}%</b></td>
      <td class="n">${fmtK(c.tokens.gpt4o.raw)} → ${fmtK(c.tokens.gpt4o.rtk)}</td><td class="n">${fmtK(c.tokens.claude.raw)} → ${fmtK(c.tokens.claude.rtk)}</td></tr>`).join("")}
  </table></div>
  <div class="row" style="flex:1;min-height:0">
    <div class="col"><div class="lab">rtk read --max-lines 150 on an 83 KB file <span>first lines</span></div>
      <pre class="snip rtk grow" style="font-size:13px">${esc(D.snip.catRtk)}</pre></div>
    <div class="col"><div class="lab">rtk rg, grouped by file <span>first lines</span></div>
      <pre class="snip rtk grow" style="font-size:13px">${esc(D.snip.rgRtk)}</pre></div>
  </div>
</div>`);
}

// 11 ─ no gain
{
  const a = C("git_log_oneline"), b = C("npm_test");
  frame("Where rtk adds nothing", "Compact output passes through unchanged", `
<div class="row">
  <div class="col">
    <div class="lab">git log --oneline -40 <span>${fmtB(a.rawBytes)} → ${fmtB(a.rtkBytes)} (−${a.savedPct}%)</span></div>
    <pre class="snip raw" style="font-size:13px">${esc(D.snip.onelineRaw)}</pre>
    <pre class="snip rtk" style="font-size:13px">${esc(D.snip.onelineRtk)}</pre>
    <div class="card amber grow"><p style="font-size:19px">One hash and one subject per commit is already as short as it gets.
      rtk only trims trailing characters.</p></div>
  </div>
  <div class="col">
    <div class="lab">npm test (jest) <span>${fmtB(b.rawBytes)} → ${fmtB(b.rtkBytes)} (−${b.savedPct}%)</span></div>
    <pre class="snip rtk grow" style="font-size:13px">${esc(D.snip.jestRtk)}</pre>
    <div class="card amber"><p style="font-size:19px">Jest's default reporter already prints only failures plus a summary,
      so there is little left to remove.</p></div>
  </div>
  <div class="col" style="flex:.8">
    <div class="card edge grow"><h4>Exit codes, raw / rtk</h4><table class="tight">
      ${D.commands.map(c => `<tr><td class="mono" style="font-size:15px">${c.id}</td><td class="n">${c.rcRaw} / ${c.rcRtk} ${c.rcRaw===c.rcRtk?'<b class="g">✓</b>':'<b class="r">✗</b>'}</td></tr>`).join("")}
    </table></div>
  </div>
</div>`);
}

// 12 ─ tokenizers
{
  const ids = ["git_diff", "grep", "cat_huge", "rg", "git_log", "pytest"];
  const kb = D.bytesTotal.raw / 1000;
  frame("Across models", "Tokenizers disagree on counts, not on the saving", `
<div class="row">
  <div class="col">
    <div class="card"><h4>Raw tokens for the same 836 KB of output</h4>
      ${hbar(M.map(m => ({l: D.label[m], v: T[m].raw, c: D.color[m], n: `${fmtK(T[m].raw)} · ${(T[m].raw/kb).toFixed(0)} tok/KB`})),
        {w: 680, rowH: 54, padL: 120, padR: 200, fs: 20})}</div>
    <div class="card edge grow"><p style="font-size:19px">Claude's and Gemma's tokenizers split shell output about 20% finer than
      GPT-4o's and Llama's, so the same command costs more tokens there. The <b>percentage saved</b> stays between ${minS}% and ${maxS}% for all five.</p></div>
  </div>
  <div class="col">
    <div class="card grow"><h4>rtk's estimate (bytes ÷ 4) against real counts</h4><table class="tight">
      <tr><th>Raw output of</th><th class="n">bytes÷4</th><th class="n">GPT-4o</th><th class="n">Claude</th><th class="n">Qwen3</th></tr>
      ${ids.map(id => { const c = C(id); return `<tr><td class="mono" style="font-size:16px">${id}</td><td class="n">${fmtK(c.estDiv4.raw)}</td>
        <td class="n">${fmtK(c.tokens.gpt4o.raw)}</td><td class="n">${fmtK(c.tokens.claude.raw)}</td><td class="n">${fmtK(c.tokens.qwen.raw)}</td></tr>`; }).join("")}
    </table>
    <p class="small" style="margin-top:14px">rtk ships no tokenizer and estimates tokens as bytes ÷ 4. That is close for GPT-4o and Llama,
      but undercounts Claude by roughly 15–30% on code-heavy output. Percentages are unaffected.</p></div>
  </div>
</div>`);
}

// 13 ─ latency
{
  const fastIds = ["cat_mid","cat_huge","grep","rg","ls","git_log","git_log_oneline","git_status"];
  const slowIds = ["git_diff","cargo_test","npm_test","pytest"];
  const oh = c => c.msRtk - c.msRaw;
  const fo = fastIds.map(i => oh(C(i))), so = slowIds.map(i => oh(C(i)));
  const row = c => `<tr><td class="mono" style="font-size:16px">${c.id}</td><td class="n">${c.msRaw.toFixed(0)}</td><td class="n">${c.msRtk.toFixed(0)}</td>
    <td class="n"><b style="color:${oh(c)<=15?'var(--good)':'#b07800'}">+${oh(c).toFixed(0)}</b></td></tr>`;
  frame("Overhead", "rtk adds milliseconds, not seconds", `
<div class="row">
  <div class="col"><div class="card grow"><h4>Quick commands (ms, median)</h4><table class="tight">
    <tr><th>Command</th><th class="n">raw</th><th class="n">rtk</th><th class="n">added</th></tr>${fastIds.map(i => row(C(i))).join("")}</table></div></div>
  <div class="col">
    <div class="card"><h4>Larger jobs (ms, median)</h4><table class="tight">
      <tr><th>Command</th><th class="n">raw</th><th class="n">rtk</th><th class="n">added</th></tr>${slowIds.map(i => row(C(i))).join("")}</table></div>
    <div class="card edge grow"><h4>Against the "&lt;10 ms" claim</h4>
      <p style="font-size:19px">File reads stay under 10 ms. Other quick commands add ${Math.round(Math.min(...fo))}–${Math.round(Math.max(...fo))} ms,
      and larger jobs ${Math.round(Math.min(...so))}–${Math.round(Math.max(...so))} ms. The claim is optimistic, but an agent step takes seconds,
      so none of this is noticeable. The time is paid once, while the smaller output stays cheaper for the rest of the session.</p></div>
  </div>
</div>`);
}

// 14 ─ self-report
frame("Self-report vs measurement", `rtk's own dashboard shows 44.9%. Measured: ${mean}%.`, `
<div class="row">
  <div class="col" style="flex:1.25"><pre class="snip grow" style="font-size:14px">${esc(D.gainText)}</pre></div>
  <div class="col">
    <div class="card edge"><h4>Why the numbers differ</h4><p style="font-size:19px"><span class="mono">rtk gain</span> leaves out
      outputs larger than about 30,000 characters, assuming the agent would truncate them anyway. In this run that excluded
      34 of 49 tracked commands, including the 337 KB file read, the 170 KB diff and the 143 KB grep, which are the biggest savings.</p></div>
    <div class="card amber grow"><h4>Which number to use</h4><p style="font-size:19px">If your agent cuts long tool output at around 30K characters,
      expect something close to rtk's figure. If it reads everything, as in this benchmark, expect the measured one.
      The dashboard is conservative, not inflated.</p>
      <p class="small" style="margin-top:12px">The dashboard also counts my earlier probe runs, so its command total (49) is higher than 12 × reps.</p></div>
  </div>
</div>`);

// 15 ─ cost
{
  const per = 4200;
  frame("Cost", "What the saving is worth in API spend", `
<div style="display:flex;flex-direction:column;gap:22px;height:100%">
  <div class="card" style="padding:12px 20px"><table class="tight">
    <tr><th>Model, list input price</th><th class="n">Tokens raw → rtk</th><th class="n">Cost per run raw → rtk</th>
      <th class="n">Saved per run</th><th class="n">Saved per month*</th></tr>
    ${M.map(m => { const t = T[m], p = D.price[m].p, a = t.raw/1e6*p, b = t.rtk/1e6*p;
      return `<tr><td><span class="dot" style="background:${D.color[m]}"></span><b>${D.label[m]}</b>
        <span class="small" style="font-size:15px"> $${p.toFixed(2)}/M · ${D.price[m].src}</span></td>
        <td class="n">${fmtK(t.raw)} → ${fmtK(t.rtk)}</td><td class="n">$${a.toFixed(3)} → $${b.toFixed(3)}</td>
        <td class="n"><b class="g">$${(a-b).toFixed(3)}</b></td><td class="n"><b class="g">$${Math.round((a-b)*per).toLocaleString()}</b></td></tr>`; }).join("")}
  </table></div>
  <div class="row" style="flex:1;min-height:0">
    <div class="card amber" style="flex:1"><h4>Why your bill drops by less than 88%</h4><p style="font-size:19px">Shell output is only part of the input:
      the system prompt, your messages and file context are untouched, and output tokens are not affected at all. If shell output is
      a third of your input tokens, an 88% cut lowers input spend by about 29%.</p></div>
    <div class="card edge" style="flex:1"><h4>Why it still adds up</h4><p style="font-size:19px">Every output stays in the conversation and is re-sent
      on each later turn, so a smaller output saves again and again. It also leaves more of the context window for real work.</p>
      <p class="small" style="margin-top:12px">* Hypothetical team: 10 developers × 20 workloads like this per day × 21 working days = ${per.toLocaleString()} runs. List prices, no cache or batch discounts.</p></div>
  </div>
</div>`);
}

// agents ─ integrations overview
const AG = k => (D.agents || []).find(a => a.key === k);
frame("Agents", "Three coding agents, three ways to plug rtk in", `
<div style="display:flex;flex-direction:column;gap:20px;height:100%">
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:22px;flex:1;min-height:0">
    ${[["Claude Code", "Official · rtk init -g", "A <span class=\"mono\">PreToolUse</span> hook on the Bash tool. rtk returns the rewritten command and Claude Code runs it.",
        "~/.claude/settings.json\n{\"hooks\": {\"PreToolUse\": [{\n  \"matcher\": \"Bash\",\n  \"hooks\": [{\"type\": \"command\",\n    \"command\": \"rtk hook claude\"}]\n}]}}",
        "Large output goes to a file; the model sees a 2 KB preview.", AG("claude")],
       ["Droid", "Official · rtk init -g --agent droid", "A <span class=\"mono\">PreToolUse</span> hook on the Execute tool. Droid's own permission flow approves the rewritten command.",
        "~/.factory/hooks.json\n{\"PreToolUse\": [{\n  \"matcher\": \"Execute\",\n  \"hooks\": [{\"type\": \"command\",\n    \"command\": \"rtk hook droid\"}]\n}]}",
        "Keeps about 10K chars of each result; the rest goes to a log file.", AG("droid")],
       ["Amp", "No rtk support · plugin built here", "A <span class=\"mono\">tool.call</span> handler in Amp's plugin API returns <span class=\"mono\">modify</span> with the rtk command (slide 19).",
        "~/.config/amp/plugins/rtk.ts\namp.on('tool.call', async (e, ctx) => {\n  // rtk rewrite <command>\n  return { action: 'modify',\n    input: { ...e.input, command } }\n})",
        "Cuts each tool result at 50,000 chars.", AG("amp")]].map(([n, tag, how, code, cap, a]) => `
      <div class="card edge" style="display:flex;flex-direction:column;gap:12px;padding:18px 22px">
        <div style="display:flex;justify-content:space-between;align-items:baseline"><div style="font-size:26px;font-weight:700">${n}</div><span class="pill">${tag}</span></div>
        <p style="font-size:17px">${how}</p>
        <pre class="snip code" style="font-size:13px;margin:0">${esc(code)}</pre>
        <div style="font-size:16px"><b>Agent's own output limit:</b> ${cap}</div>
        ${a ? `<div class="mono" style="margin-top:auto;font-size:15px;color:var(--muted)">model ${a.model || "chosen by Amp"} · correct ${a.offOk.join("·")} → <b class="g">${a.onOk.join("·")}</b></div>` : ""}
      </div>`).join("")}
  </div>
  <div class="card note" style="padding:14px 22px"><h4 style="margin-bottom:6px">One protocol for all three</h4><p style="font-size:16.5px">Same prompt: run
    <span class="mono">git status</span>, <span class="mono">git log -40</span>, <span class="mono">git diff HEAD~12</span>, <span class="mono">rg -n "pub fn" src</span>,
    <span class="mono">cargo test</span>, then answer 7 questions as JSON, scored by exact match. 3 fresh threads per side, rtk on and off alternating.
    The hook is added per run with <span class="mono">--settings</span>; global agent configs are untouched. Each agent uses its default model.</p></div>
</div>`);

// agents ─ per-agent results
function agentSlide(a, read, setup) {
  if (!a) return;
  const pct = v => `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;
  const avg = xs => (xs.reduce((s, x) => s + x, 0) / xs.length).toFixed(1);
  const costFmt = a.costUnit === "USD" ? (v => "$" + v.toFixed(2)) : (v => fmtK(v));
  const mrow = (label, k, fmt) => a.m[k] ? `<tr><td>${label}</td><td class="n">${fmt(a.m[k].off)}</td><td class="n">${fmt(a.m[k].on)}</td>
    <td class="n"><b class="${a.m[k].d < 0 ? "g" : "r"}">${pct(a.m[k].d)}</b></td></tr>` : "";
  const QN = {modified_not_staged: "Modified, not staged", untracked_entries: "Untracked entries", latest_commit_author: "Latest commit author",
    oldest_commit_author_of_40: "Oldest author of 40", diff_files_changed: "Files changed in diff", rg_files_with_pub_fn: "Files with pub fn",
    cargo_failed_tests: "Failed cargo tests"};
  const missed = Object.entries(a.miss).filter(([, v]) => v.off || v.on);
  const tag = n => n === "preview" ? ` <span class="pill">2 KB preview</span>` : n === "truncated" ? ` <span class="pill">cut</span>` : "";
  frame(a.name + " results", `${a.name}: ${avg(a.offOk)} → ${avg(a.onOk)} of 7 answers correct, context ${pct(a.ctx)}`, `
<div class="row">
  <div class="col" style="flex:1">
    <div class="card" style="padding:12px 20px"><h4 style="margin-bottom:6px">Mean of ${a.n} threads per side · ${a.model}</h4><table class="tight">
      <tr><th>Metric</th><th class="n">No rtk</th><th class="n">rtk hook</th><th class="n">Δ</th></tr>
      ${mrow("Tool output to model (chars)", "chars", fmtK)}
      ${mrow("Context tokens (all turns)", "ctx", fmtK)}
      ${mrow("Output tokens", "out", fmtK)}
      ${mrow("Wall time (s)", "wall", v => v.toFixed(1))}
      ${mrow("Cost (" + a.costUnit + ")", "cost", costFmt)}
      <tr><td>Answers correct, per run</td><td class="n">${a.offOk.join(" · ")}</td><td class="n"><b class="g">${a.onOk.join(" · ")}</b></td><td class="n"></td></tr>
    </table></div>
    <div class="card grow" style="padding:12px 20px"><h4 style="margin-bottom:6px">Questions missed (runs of ${a.n})</h4><table class="tight">
      <tr><th>Question</th><th class="n">No rtk</th><th class="n">rtk hook</th></tr>
      ${missed.map(([q, v]) => `<tr><td>${QN[q] || q}</td><td class="n"><b class="${v.off ? "r" : ""}">${v.off}</b></td><td class="n"><b class="${v.on ? "r" : ""}">${v.on}</b></td></tr>`).join("")}
    </table></div>
  </div>
  <div class="col" style="flex:1.05">
    <div class="card" style="padding:12px 20px"><h4 style="margin-bottom:6px">What the model received per command (chars, median)</h4><table class="tight">
      <tr><th>Command</th><th class="n">No rtk</th><th class="n">rtk hook</th></tr>
      ${a.perCmd.map(c => `<tr><td class="mono" style="font-size:15px">${esc(c.cmd)}</td><td class="n">${fmtK(c.off)}${tag(c.offNote)}</td><td class="n">${fmtK(c.on)}${tag(c.onNote)}</td></tr>`).join("")}
    </table></div>
    <div class="card edge" style="padding:14px 20px"><h4 style="margin-bottom:6px">Reading it</h4><p style="font-size:16px;line-height:1.45">${read}</p></div>
    <div class="card amber grow" style="padding:14px 20px"><h4 style="margin-bottom:6px">Setup finding</h4><p style="font-size:15.5px;line-height:1.45">${setup}</p></div>
  </div>
</div>`, `agents/${a.key}_results.json`);
}
agentSlide(AG("claude"),
  `Claude Code moves large Bash output to a file and shows the model a 2 KB preview. Without rtk, the 168 KB diff and 56 KB rg output arrived only as
   previews, so the file counts were guessed or left empty. rtk's 23 KB and 18 KB summaries fit and were read in full: more tokens, every answer correct.`,
  `On Windows, Claude Code also offers a PowerShell tool that rtk's Bash hook never sees. In a first attempt the model used it and rtk was bypassed;
   those runs were discarded and PowerShell was disabled on both sides. Cost is Claude Code's own report; one cold-cache rtk run cost $1.41.`);
agentSlide(AG("droid"),
  `Droid keeps about 10K characters of each result. Without rtk, git log, the diff and rg were all cut, and both file counts were lost in every run.
   With rtk, git log fits whole; the diff and rg summaries are still cut, but their totals survived. rtk shortens git log lines to ~120 chars, so the newest
   commit's author appears as "&lt;Nicolas..." and was missed in every rtk run.`,
  `Droid runs hooks without the user PATH on Windows, so the hook needs rtk's absolute path. rtk leaves approval to Droid, and medium autonomy does not
   auto-approve rewritten <span class="mono">rtk …</span> commands: add them to <span class="mono">commandAllowlist</span> or use
   <span class="mono">--auto high</span> (used on both sides here).`);

// 16 ─ Amp integration
frame("Amp integration", "Integrating rtk into Amp through the plugin API", `
<div style="display:flex;flex-direction:column;gap:20px;height:100%">
  <div class="flow">
    <div class="nd">Amp model<small>emits shell_command</small></div><div class="ar">→</div>
    <div class="nd hl">tool.call event<small>rtk.ts plugin</small></div><div class="ar">→</div>
    <div class="nd hl">rtk rewrite "git status"<small>exit 0/3 → rtk git status</small></div><div class="ar">→</div>
    <div class="nd">{action: "modify"}<small>input.command replaced</small></div><div class="ar">→</div>
    <div class="nd">Compact result<small>returned to the model</small></div>
  </div>
  <div class="row" style="flex:1;min-height:0">
    <div class="col" style="flex:1.15">
      <div class="lab">~/.config/amp/plugins/rtk.ts <span>core handler, ${D.ampPluginLines} lines total</span></div>
      <pre class="snip code grow" style="font-size:13px;line-height:1.4">${D.ampPluginCode}</pre>
    </div>
    <div class="col" style="gap:16px">
      <div class="card edge" style="padding:16px 22px"><h4 style="margin-bottom:8px">Integration level</h4><p style="font-size:17px">rtk v${D.rtkVersion} ships no Amp support.
        Amp's <span class="mono">tool.call</span> event can <b>modify</b> a tool's input before it runs: the same position as rtk's
        Claude Code PreToolUse hook. Transparent, every thread, no prompt changes.</p></div>
      <div class="card amber" style="padding:16px 22px"><h4 style="margin-bottom:8px">Guards added in the plugin</h4><ol class="num amber">
        <li style="font-size:16px;margin-bottom:8px"><span class="mono">python -m X</span> is left as typed (rtk's <span class="mono">rtk pytest</span> picked a broken pytest.exe here).</li>
        <li style="font-size:16px;margin-bottom:8px"><span class="mono">rtk …</span> commands pass through; <span class="mono">RTK_AMP_DISABLE=1</span> turns it off.</li>
        <li style="font-size:16px;margin-bottom:0">rtk exit 2 with a message becomes <span class="mono">reject-and-continue</span>.</li></ol></div>
      <div class="card note grow" style="padding:16px 22px"><h4 style="margin-bottom:8px">Verified in a live Amp thread</h4>
        <pre class="snip rtk" style="font-size:12.5px;margin-bottom:8px;padding:8px 12px">rtk rewrite: git status -> rtk git status
rtk rewrite: git log -40 -> rtk git log -40
rtk rewrite: git diff HEAD~12 -> rtk git diff HEAD~12
rtk rewrite: rg -n "pub fn" src -> rtk rg -n "pub fn" src
rtk rewrite: cargo test -> rtk cargo test</pre>
        <p style="font-size:15px;line-height:1.4">Plugin log; 6 of 7 answers correct from compressed output. Amp's built-in Read/Grep/glob tools bypass the shell and are not covered.</p></div>
    </div>
  </div>
</div>`, "Amp CLI " + D.ampVersion);

// 17 ─ Amp results
if (D.amp) {
  const A = D.amp;
  const mrow = (label, k, fmt, good) => `<tr><td>${label}</td><td class="n">${fmt(A.off[k])}</td><td class="n">${fmt(A.on[k])}</td>
    <td class="n"><b class="${(A.d[k] < 0) === good ? 'g' : 'r'}">${A.d[k] > 0 ? '+' : ''}${A.d[k]}%</b></td></tr>`;
  frame("Amp results", `Amp end to end: ${Math.round(-A.d.chars)}% less tool output, ${Math.round(-A.d.ctx)}% fewer context tokens`, `
<div class="row">
  <div class="col" style="flex:1.1">
    <div class="card" style="padding:14px 22px"><h4>Table 3 · Same task, mean of ${A.n} threads per side</h4><table class="tight">
      <tr><th>Metric</th><th class="n">No rtk</th><th class="n">rtk plugin</th><th class="n">Δ</th></tr>
      ${mrow("Tool output returned to model (chars)", "chars", fmtK, true)}
      ${mrow("Context tokens processed (all turns)", "ctx", fmtK, true)}
      ${mrow("Uncached input tokens (new + cache write)", "newIn", fmtK, true)}
      ${mrow("Cache-read tokens", "cacheRead", fmtK, true)}
      ${mrow("Output tokens", "out", v => fmtK(v), true)}
      ${mrow("Wall time (s)", "wall", v => v.toFixed(1), true)}
      <tr><td>Answers correct (of 7 per run)</td><td class="n">${A.off.correctAll}</td><td class="n">${A.on.correctAll}</td><td class="n"></td></tr>
    </table>
    <div class="fig">Model and harness chosen by Amp; one fresh thread per run; runs alternated on/off.</div></div>
    <div class="card grow" style="padding:12px 22px"><h4 style="margin-bottom:6px">Per-run detail</h4><table class="tight">
      <tr><th style="padding:5px 12px">Run</th><th class="n" style="padding:5px 12px">Tool chars</th><th class="n" style="padding:5px 12px">Context tok</th><th class="n" style="padding:5px 12px">Correct</th><th class="n" style="padding:5px 12px">Wall s</th></tr>
      ${[...A.runs].sort((a, b) => a.idx - b.idx || (a.side < b.side ? 1 : -1)).map(r => `<tr><td class="mono" style="font-size:14px;padding:3px 12px">${r.side === "on" ? "rtk" : "raw"} #${r.idx+1}</td><td class="n" style="font-size:15px;padding:3px 12px">${fmtK(r.tool_result_chars)}</td>
        <td class="n" style="font-size:15px;padding:3px 12px">${fmtK(r.context_tokens)}</td><td class="n" style="font-size:15px;padding:3px 12px">${r.correct}/7</td><td class="n" style="font-size:15px;padding:3px 12px">${r.wall_s}</td></tr>`).join("")}
    </table></div>
  </div>
  <div class="col">
    <div class="card edge"><h4>The task</h4><p style="font-size:17px">Run <span class="mono">git status</span>, <span class="mono">git log -40</span>,
      <span class="mono">git diff HEAD~12</span>, <span class="mono">rg -n "pub fn" src</span> and <span class="mono">cargo test</span>, then answer 7 factual
      questions as JSON. Scoring is exact match against ground truth.</p></div>
    <div class="card grow"><h4>Reading the numbers</h4><p style="font-size:17px">${A.note}</p></div>
  </div>
</div>`, "amp/amp_results.json");
}

// agents compared ─ scoreboard and failures
if (D.agents && D.agents.length > 1) {
  const G = D.agents;
  const avg = xs => xs.reduce((s, x) => s + x, 0) / xs.length;
  const AC = {claude: "#c96442", droid: "#3d7cdb", amp: "#d98e04", amp_wsl: "#b07300"};
  const sgn = v => (v > 0 ? "+" : "") + Math.round(v) + "%";

  // Amp ran on two machines; rank it once, on the pooled runs.
  const groups = {};
  G.forEach(a => { const k = a.key.startsWith("amp") ? "amp" : a.key; (groups[k] = groups[k] || []).push(a); });
  const rank = Object.entries(groups).map(([k, as]) => {
    const n = as.reduce((s, a) => s + a.n, 0);
    const missOn = q => as.reduce((s, a) => s + a.miss[q].on, 0), missOff = q => as.reduce((s, a) => s + a.miss[q].off, 0);
    return {k, name: k === "amp" ? "Amp" : as[0].name, model: k === "amp" ? "model chosen by Amp" : as[0].model, n,
      off: avg(as.flatMap(a => a.offOk)), on: avg(as.flatMap(a => a.onOk)),
      perfect: as.flatMap(a => a.onOk).filter(x => x === 7).length,
      ctx: avg(as.map(a => a.ctx)), chars: avg(as.map(a => a.chars)), missOn, missOff, color: AC[k]};
  }).sort((a, b) => b.on - a.on || a.ctx - b.ctx);
  const W = rank[0];

  function divbar(items, o) {
    const Wd = o.w, rowH = o.rowH, L = o.padL, R = o.padR, top = 6, H = items.length * rowH + top + 30;
    const x = v => L + (v - o.min) / (o.max - o.min) * (Wd - L - R);
    const mono = 'font-family="Cascadia Mono,Consolas,monospace"';
    let s = `<svg viewBox="0 0 ${Wd} ${H}" width="${Wd}" height="${H}">`;
    o.ticks.forEach(v => {
      s += `<line x1="${x(v)}" y1="${top}" x2="${x(v)}" y2="${H - 26}" stroke="${v === 0 ? "#1c2430" : "#e3e8ee"}" stroke-width="${v === 0 ? 1.5 : 1}"/>`;
      s += `<text x="${x(v)}" y="${H - 8}" text-anchor="middle" font-size="13" fill="#8a95a5" ${mono}>${v > 0 ? "+" : ""}${v}%</text>`;
    });
    items.forEach((it, i) => {
      const cy = top + i * rowH + rowH / 2, x0 = x(0), x1 = x(it.v);
      s += `<text x="${L - 12}" y="${cy + 5}" text-anchor="end" font-size="${o.fs}" font-weight="600" fill="#1c2430">${it.l}</text>`;
      s += `<rect x="${Math.min(x0, x1)}" y="${cy - 11}" width="${Math.max(2, Math.abs(x1 - x0))}" height="22" fill="${it.v < 0 ? "#1f8a5b" : "#c2410c"}"/>`;
      s += `<text x="${(it.v < 0 ? x0 : x1) + 8}" y="${cy + 5}" font-size="${o.fs - 1}" font-weight="700" fill="${it.v < 0 ? "#17784c" : "#b4380b"}" ${mono}>${sgn(it.v)}</text>`;
    });
    return s + `</svg>`;
  }
  const short = a => a.key === "amp" ? "Amp · Win" : a.key === "amp_wsl" ? "Amp · WSL" : a.name;
  const chartOpts = {w: 440, rowH: 50, padL: 112, padR: 20, fs: 16};

  frame("Agents compared", `Winner: ${W.name} with rtk, ${W.on.toFixed(1)} of 7 answers correct`, `
<div style="display:flex;flex-direction:column;gap:18px;height:100%">
  <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:20px">
    <div class="card" style="padding:12px 16px"><div class="lab" style="font-size:14px">Answers correct, of 7 <span><span class="dot" style="background:#b8c1cc"></span>no rtk colored = rtk</span></div>
      ${hbar(G.map(a => ({l: short(a), v: avg(a.offOk), v2: avg(a.onOk), c: AC[a.key],
        n: `${avg(a.offOk).toFixed(1)}→${avg(a.onOk).toFixed(1)}`})), {...chartOpts, max: 7, fs: 16, padR: 86, tickFmt: v => v.toFixed(v % 1 ? 2 : 0)})}
      <div class="fig">Higher is better · mean of ${G[0].n} threads per side</div></div>
    <div class="card" style="padding:12px 16px"><div class="lab" style="font-size:14px">Context tokens, rtk vs no rtk <span>lower is better</span></div>
      ${divbar(G.map(a => ({l: short(a), v: a.ctx})), {...chartOpts, min: -40, max: 40, ticks: [-40, -20, 0, 20, 40]})}
      <div class="fig">All tokens processed over the whole thread</div></div>
    <div class="card" style="padding:12px 16px"><div class="lab" style="font-size:14px">Tool output read by the model <span>lower is better</span></div>
      ${divbar(G.map(a => ({l: short(a), v: a.chars})), {...chartOpts, padR: 52, min: -100, max: 100, ticks: [-100, -50, 0, 50, 100]})}
      <div class="fig">Characters of command output returned to the model</div></div>
  </div>
  <div class="row" style="flex:1;min-height:0;gap:20px">
    <div class="card edge" style="flex:1.55;padding:14px 22px"><h4 style="margin-bottom:8px">Ranking · accuracy first, then tokens</h4>
      ${rank.map((r, i) => `<div style="display:flex;gap:16px;align-items:flex-start;padding:7px 0;${i ? "border-top:1px solid var(--line2)" : ""}">
        <div class="mono" style="font-size:30px;font-weight:700;line-height:1;width:34px;color:${i === 0 ? "var(--good)" : "var(--faint)"}">${i + 1}</div>
        <div style="flex:1"><div style="font-size:19px;font-weight:700"><span class="dot" style="background:${r.color}"></span>${r.name}
          <span class="mono" style="font-size:13px;font-weight:400;color:var(--faint)">${r.model}</span>
          <span class="mono" style="font-size:16px;float:right">${r.off.toFixed(1)} → <b class="g">${r.on.toFixed(1)}</b> of 7 · context ${sgn(r.ctx)}</span></div>
          <div style="font-size:15.5px;color:var(--muted);margin-top:2px">${{
            claude: `Only agent with every rtk run at 7/7. rtk's full diff and rg summaries replaced 2 KB previews. The price: more context (${sgn(r.ctx)}) and a higher bill.`,
            amp: `Same accuracy gain plus the biggest token cut (${sgn(r.ctx)} context, ${sgn(r.chars)} tool output) on two machines. Lost the newest commit author in ${r.missOn("latest_commit_author")} of ${r.n} rtk runs.`,
            droid: `Smallest gain. Droid's ~10K cap still cuts rtk's diff and rg summaries, and rtk's shortened git log hid the newest author in ${r.missOn("latest_commit_author")} of ${r.n} runs.`
          }[r.k]}</div></div></div>`).join("")}
    </div>
    <div class="card note" style="flex:1;padding:14px 22px"><h4 style="margin-bottom:8px">What was tested</h4><p style="font-size:15.5px;line-height:1.45">
      Each agent got the same prompt: run <span class="mono">git status</span>, <span class="mono">git log -40</span>, <span class="mono">git diff HEAD~12</span>,
      <span class="mono">rg -n "pub fn" src</span> and <span class="mono">cargo test</span> on the rtk repository, then answer 7 factual questions (file counts, authors,
      failing tests) as JSON, scored against ground truth. ${G[0].n} fresh threads with rtk and ${G[0].n} without, alternating.</p>
      <p class="small" style="margin-top:8px;font-size:14.5px">"Winner" means agent <i>and</i> its default model as shipped: claude-fable-5-1, gpt-6.1-sol, and Amp's own choice.
      Three runs per side and one task: a direction, not a league table.</p></div>
  </div>
</div>`, "agents/*_results.json · amp/amp_results*.json");

  const QN = {latest_commit_author: "Newest commit's author", diff_files_changed: "Files changed in the diff", rg_files_with_pub_fn: "Files containing pub fn",
    modified_not_staged: "Modified, not staged", untracked_entries: "Untracked entries", oldest_commit_author_of_40: "Oldest author of 40", cargo_failed_tests: "Failed cargo tests"};
  const qs = Object.keys(QN).filter(q => rank.some(r => r.missOff(q) || r.missOn(q)));
  const cell = (n, of) => `<b class="${n ? "r" : "g"}">${n}/${of}</b>`;
  frame("Agents compared", "What each agent failed on, and what that means in practice", `
<div class="row">
  <div class="col" style="flex:1.05">
    <div class="card" style="padding:12px 20px"><h4 style="margin-bottom:6px">Runs with a wrong or empty answer · no rtk → rtk</h4><table class="tight">
      <tr><th>Question</th>${rank.map(r => `<th class="n"><span class="dot" style="background:${r.color}"></span>${r.name}</th>`).join("")}</tr>
      ${qs.map(q => `<tr><td>${QN[q]}</td>${rank.map(r => `<td class="n">${cell(r.missOff(q), r.n)} → ${cell(r.missOn(q), r.n)}</td>`).join("")}</tr>`).join("")}
      <tr><td colspan="${rank.length + 1}" class="small" style="font-size:14px">Every other question was answered correctly in every run, by every agent.</td></tr>
    </table></div>
    <div class="card grow" style="padding:12px 20px"><h4 style="margin-bottom:6px">Why</h4><table class="tight">
      <tr><th style="width:18%">Agent</th><th>Without rtk</th><th>With rtk</th></tr>
      <tr><td><b>Claude Code</b></td><td style="font-size:15.5px">Diff and rg saved to a file; the model saw only a 2 KB preview and guessed the counts.</td><td style="font-size:15.5px">Nothing missed.</td></tr>
      <tr><td><b>Droid</b></td><td style="font-size:15.5px">git log, diff and rg cut at ~10K chars; both file counts lost.</td><td style="font-size:15.5px">Counts survive in rtk's summary; newest author lost in the shortened git log line.</td></tr>
      <tr><td><b>Amp</b></td><td style="font-size:15.5px">Diff and rg cut at 50K chars; both file counts lost.</td><td style="font-size:15.5px">Same author loss as Droid in most runs.</td></tr>
    </table></div>
  </div>
  <div class="col">
    <div class="card edge grow" style="padding:14px 22px"><h4 style="margin-bottom:8px">Implications in real work</h4><ol class="num">
      <li style="font-size:16.5px;margin-bottom:9px"><b>Without rtk, the risk is silent wrong answers, not cost.</b> Every agent clips big output, and the model then guesses:
        "how many files does this PR touch?", "where is this function used?" on a large repo.</li>
      <li style="font-size:16.5px;margin-bottom:9px"><b>rtk makes big output fit.</b> Totals and structure survive, so these questions get answered. It pays off most on large
        repos, long diffs, wide searches and test suites.</li>
      <li style="font-size:16.5px;margin-bottom:9px"><b>Don't plan on a smaller bill.</b> Context ranged from ${sgn(Math.min(...G.map(a => a.ctx)))} to ${sgn(Math.max(...G.map(a => a.ctx)))};
        in Claude Code, rtk raised the cost because the model finally read the whole summary.</li>
      <li style="font-size:16.5px;margin-bottom:9px"><b>rtk drops details.</b> Shortened lines and "+N more" can hide the one fact you need. For exact details,
        let the agent use <span class="mono">rtk recall</span> or rerun with <span class="mono">RTK_DISABLED=1</span>.</li>
      <li style="font-size:16.5px;margin-bottom:0"><b>Check what the hook covers.</b> PowerShell in Claude Code and built-in read/grep tools bypass rtk.</li></ol></div>
    <div class="card amber" style="padding:12px 22px"><p style="font-size:16px"><b>Pick by need:</b> best answers → Claude Code + rtk.
      Lowest tokens with the same gain → Amp + rtk. Droid gains least from rtk on Windows today.</p></div>
  </div>
</div>`, "agents/*_results.json · amp/amp_results*.json");
}

// 18 ─ verdict
frame("Verdict", "rtk is worth installing for agent-driven development", `
<div class="row">
  <div class="col" style="flex:1.1"><div class="card edge grow"><h4>What I found</h4><ol class="num">
    <li><b>${minS}–${maxS}% fewer tokens</b> on this 12-command workload, with every tokenizer tested.</li>
    <li>Savings follow output size: file reads 95–99%, grep 88%, diffs 86%, pytest and cargo test 62–88%.</li>
    <li>Compact output passes through unchanged and exit codes matched on all 12 commands.</li>
    <li>Truncated content can be recovered with <span class="mono">rtk recall &lt;id&gt;</span>.</li>
    <li>Overhead is tens of milliseconds, more than the "&lt;10 ms" headline but negligible in practice.</li>
    <li>In Amp, Claude Code and Droid, answers improved (5→6–7 of 7) because compressed output fits under each agent's own output limit.</li></ol></div></div>
  <div class="col">
    <div class="card amber"><h4>Watch out for</h4><ol class="num amber">
      <li><span class="mono">rtk read</span> needs <span class="mono">--max-lines</span> to get the big file savings.</li>
      <li>Windows gaps: <span class="mono">rtk tree</span> sends Linux flags to Windows <span class="mono">tree</span> and fails.</li>
      <li>Compression is lossy: pytest showed 10 of 12 failures by name, and shortened git log lines hid the newest author from Amp and Droid.</li>
      <li>Hooks only see the shell tool they match: Claude Code's PowerShell tool and agents' built-in read/grep tools bypass rtk.</li></ol></div>
    <div class="card edge grow" style="background:var(--blue-bg)"><h4 style="color:var(--blue)">Recommendation</h4>
      <p style="font-size:18px">Install it with <span class="mono">rtk init -g</span> for your agent. Command output shrinks by half to nine-tenths;
      inside Amp, Claude Code and Droid that mostly showed up as better answers on large outputs, with context ${D.agents ? `between ${Math.round(Math.min(...D.agents.map(a => a.ctx)))}% and +${Math.round(Math.max(...D.agents.map(a => a.ctx)))}%` : "changing less than raw output"}.</p>
      <p class="small" style="margin-top:10px">This study compares rtk with no tool, not with other output compressors.</p></div>
  </div>
</div>`);

// 17 ─ appendix
frame("Appendix", "Full results", `
<div class="card" style="padding:10px 18px"><table class="tight">
  <tr><th>Command</th>${M.map(m => `<th class="n" style="color:${D.color[m]}">${D.label[m]}</th>`).join("")}<th class="n">Bytes</th><th class="n">Saved</th></tr>
  ${D.commands.map(c => `<tr><td class="mono" style="font-size:15px">${c.id}</td>
    ${M.map(m => `<td class="n" style="font-size:16px">${fmtK(c.tokens[m].raw)} → ${fmtK(c.tokens[m].rtk)}</td>`).join("")}
    <td class="n" style="font-size:16px">${fmtB(c.rawBytes)} → ${fmtB(c.rtkBytes)}</td><td class="n"><b class="g">${c.savedPct}%</b></td></tr>`).join("")}
  <tr style="border-top:2px solid var(--ink)"><td><b>Total</b></td>${M.map(m => `<td class="n" style="font-size:16px"><b>${fmtK(T[m].raw)} → ${fmtK(T[m].rtk)}</b></td>`).join("")}
    <td class="n" style="font-size:16px"><b>${fmtB(D.bytesTotal.raw)} → ${fmtB(D.bytesTotal.rtk)}</b></td><td class="n"><b class="g">${D.bytesTotal.saved_pct}%</b></td></tr>
</table></div>`, "tokens shown raw → rtk");

// 18 ─ contact
slides.push({sec: "Contact", html: `
<div style="position:absolute;inset:0;display:flex">
  <div style="flex:1;background:#f3f6fa;border-right:1px solid var(--line);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:18px">
    <img src="${D.photo}" style="width:260px;height:260px;border-radius:2px;object-fit:cover;border:1px solid var(--line)" alt="Daniel Liezrowice">
    <div style="font-size:38px;font-weight:700">Daniel Liezrowice</div>
    <div style="font-size:22px;color:var(--muted)">Engineering Software Lab (ESL)</div>
    <div style="font-size:21px;text-align:center;line-height:1.9"><a href="${LINKEDIN}" target="_blank">linkedin.com/in/liezrowice</a><br>
      <a href="${ESL}" target="_blank">eswlab.com</a></div>
  </div>
  <div style="flex:1.2;padding:80px 80px;display:flex;flex-direction:column">
    <a href="${ESL}" target="_blank"><img src="${D.logo}" style="height:80px" alt="ESL"></a>
    <h2 style="font-size:46px;margin-top:50px">Thank you</h2>
    <div style="width:120px;height:5px;background:var(--amber);margin:22px 0 28px"></div>
    <p class="lead">Everything behind these numbers is public. Rerun it on your own machine, or point it at your own repository.</p>
    <div class="card edge" style="margin-top:30px"><h4>Reproduce</h4>
      <pre class="snip" style="font-size:16px;background:#fff">git clone ${D.repoUrl}
cd rtk-token-benchmark
pwsh ./setup.ps1          # rtk, repo, tokenizers, suites
python bench.py           # writes results.json
python build_presentation.py</pre></div>
    <p style="margin-top:auto;font-size:20px"><a href="${D.repoUrl}" target="_blank">${D.repoUrl.replace("https://","")}</a> · MIT licence ·
      rtk itself: <a href="https://github.com/rtk-ai/rtk" target="_blank">github.com/rtk-ai/rtk</a></p>
  </div>
</div>`});

// ── mount
const stage = document.getElementById("stage");
stage.innerHTML = slides.map((s, i) => `<section class="slide">${s.html.replace("__PAGE__", `<span class="pg">${String(i+1).padStart(2,"0")} / ${slides.length}</span>`)}</section>`).join("");
const secs = [...stage.querySelectorAll(".slide")];
const prev = document.getElementById("prev"), next = document.getElementById("next");
let cur = 0;
function go(n) {
  cur = Math.max(0, Math.min(secs.length - 1, n));
  secs.forEach((s, i) => s.classList.toggle("active", i === cur));
  prev.disabled = cur === 0; next.disabled = cur === secs.length - 1;
  document.getElementById("pos").textContent = `${String(cur+1).padStart(2,"0")} / ${secs.length}`;
  document.querySelector("#track i").style.width = ((cur + 1) / secs.length * 100) + "%";
  history.replaceState(null, "", "#" + (cur + 1));
}
prev.onclick = () => go(cur - 1);
next.onclick = () => go(cur + 1);
document.getElementById("home").onclick = () => go(0);
function fit() { document.documentElement.style.setProperty("--s", Math.min(innerWidth / 1600, innerHeight / 900)); }
addEventListener("resize", fit); fit();
addEventListener("keydown", e => {
  if (["ArrowRight", " ", "PageDown"].includes(e.key)) { e.preventDefault(); go(cur + 1); }
  if (["ArrowLeft", "PageUp"].includes(e.key)) { e.preventDefault(); go(cur - 1); }
  if (e.key === "Home") go(0);
  if (e.key === "End") go(secs.length - 1);
});
let tx = null;
addEventListener("touchstart", e => { tx = e.touches[0].clientX; }, {passive: true});
addEventListener("touchend", e => { if (tx === null) return; const dx = e.changedTouches[0].clientX - tx;
  if (Math.abs(dx) > 50) go(cur + (dx < 0 ? 1 : -1)); tx = null; });
go((parseInt(location.hash.slice(1)) || 1) - 1);
</script>
</body>
</html>
"""

with open(os.path.join(BASE, "deck_style.css"), encoding="utf-8") as f:
    TEMPLATE = TEMPLATE.replace("__CSS__", f.read())
path = os.path.join(BASE, "presentation.html")
with open(path, "w", encoding="utf-8") as f:
    f.write(TEMPLATE.replace("__DATA_JSON__", json.dumps(DATA).replace("</", "<\\/")))
print("wrote", path, os.path.getsize(path), "bytes")
