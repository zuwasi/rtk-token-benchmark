"""Probe: run each command raw vs via rtk, report output sizes to pick invocations."""
import os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import shutil
import subprocess
import sys

RTK = BASE + r"\rtk-bin\rtk.exe"
REPO = BASE + r"\repo"
PY = BASE + r"\work\pyproj"
RS = BASE + r"\work\rsproj"
JS = BASE + r"\work\jsproj"
VENV = BASE + r"\.venv\Scripts"

PATH_DIRS = [
    VENV,
    BASE + r"\rtk-bin",
    r"C:\Program Files\Git\usr\bin",
    r"C:\Program Files\Git\cmd",
    r"C:\Program Files\nodejs",
    os.environ["USERPROFILE"] + r"\AppData\Roaming\npm",
    os.environ["USERPROFILE"] + r"\.cargo\bin",
    r"C:\Windows\System32",
    r"C:\Windows",
]
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
}


def run(argv, cwd):
    argv = list(argv)
    exe = shutil.which(argv[0], path=ENV["PATH"])
    if exe:
        argv[0] = exe
    p = subprocess.run(argv, cwd=cwd, env=ENV, capture_output=True)
    return p.stdout, p.stderr, p.returncode


PAIRS = [
    ("git_status", REPO, ["git", "status"], [RTK, "git", "status"]),
    ("git_log", REPO, ["git", "log", "-40"], [RTK, "git", "log", "-40"]),
    ("git_diff", REPO, ["git", "diff", "HEAD~12"], [RTK, "git", "diff", "HEAD~12"]),
    ("ls", REPO, ["ls", "-la"], [RTK, "ls", "-la"]),
    ("find", REPO, ["find", ".", "-name", "*.rs", "-not", "-path", "./.git/*"],
     [RTK, "find", ".", "-name", "*.rs", "-not", "-path", "./.git/*"]),
    ("cat_mid", REPO, ["cat", "src/hooks/permissions.rs"],
     [RTK, "read", "src/hooks/permissions.rs"]),
    ("cat_huge", REPO, ["cat", "src/cmds/git/diff_cmd.rs"],
     [RTK, "read", "src/cmds/git/diff_cmd.rs"]),
    ("rg", REPO, ["rg", "-n", "pub fn", "src"], [RTK, "rg", "-n", "pub fn", "src"]),
    ("grep", REPO, ["grep", "-rn", "unwrap()", "src"], [RTK, "grep", "-rn", "unwrap()", "src"]),
    ("tree", REPO, ["cmd", "/c", "tree"], [RTK, "tree"]),
    ("pytest_test", PY, ["python", "-m", "pytest"], [RTK, "test", "python", "-m", "pytest"]),
    ("pytest_proxy", PY, ["python", "-m", "pytest"], [RTK, "pytest"]),
    ("cargo_test", RS, ["cargo", "test"], [RTK, "cargo", "test"]),
    ("npm_test", JS, ["npm.cmd", "test"], [RTK, "npm", "test"]),
]

for name, cwd, raw_argv, rtk_argv in PAIRS:
    ro, re_, rc = run(raw_argv, cwd)
    so, se, sc = run(rtk_argv, cwd)
    rtk_head = so.decode("utf-8", "replace")[:110].replace("\n", "⏎").replace("\r", "")
    print(f"{name:14s} raw={len(ro):>7}B rc={rc:<3} | rtk={len(so):>7}B rc={sc:<3} | "
          f"stderr raw={len(re_):>5}B rtk={len(se):>5}B")
    print(f"{'':14s} rtk head: {rtk_head}")
