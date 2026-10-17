"""Probe 2: debug find/cat/npm/rg invocation details."""
import os
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import shutil
import subprocess

RTK = BASE + r"\rtk-bin\rtk.exe"
REPO = BASE + r"\repo"
PY = BASE + r"\work\pyproj"
JS = BASE + r"\work\jsproj"
VENV = BASE + r"\.venv\Scripts"

PATH_DIRS = [
    VENV,
    BASE + r"\rtk-bin",
    r"C:\Program Files\Git\usr\bin",
    r"C:\Program Files\Git\cmd",
    r"C:\Program Files\nodejs",
    os.environ["USERPROFILE"] + r"\AppData\Roaming\npm",
    os.environ["USERPROFILE"] + r"\.factory\bin",
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


def run(argv, cwd):
    argv = list(argv)
    exe = shutil.which(argv[0], path=ENV["PATH"])
    if exe:
        argv[0] = exe
    p = subprocess.run(argv, cwd=cwd, env=ENV, capture_output=True)
    return p.stdout, p.stderr, p.returncode


def show(label, argv, cwd, tail=False):
    o, e, rc = run(argv, cwd)
    print(f"--- {label}: out={len(o)}B err={len(e)}B rc={rc}")
    txt = (e if e else o).decode("utf-8", "replace")
    chunk = txt[-700:] if tail else txt[:700]
    print(chunk)
    print()


# A: raw npm test stderr with fuller env
show("A raw npm.cmd test", ["npm.cmd", "test"], JS, tail=True)

# B: find simple form
show("B raw find . -name *.rs", ["find", ".", "-name", "*.rs"], REPO, tail=True)
show("B rtk find . -name *.rs", [RTK, "find", ".", "-name", "*.rs"], REPO, tail=True)

# C: rtk read behavior
show("C rtk read --help", [RTK, "read", "--help"], REPO)
o, e, rc = run([RTK, "read", "README.md"], REPO)
print(f"--- C rtk read README.md: {len(o)}B rc={rc}")
print(o.decode('utf-8', 'replace')[:400])
print()
o, e, rc = run([RTK, "read", "../work/pyproj/utils.py"], REPO)
print(f"--- C rtk read utils.py: {len(o)}B rc={rc}")
print(o.decode('utf-8', 'replace')[:400])
print()
o, e, rc = run([RTK, "cat", "README.md"], REPO)
print(f"--- C rtk cat README.md: {len(o)}B rc={rc} err={len(e)}B")
print((e or o).decode('utf-8', 'replace')[:300])
print()

# D: rg with .factory bin in PATH
show("D raw rg", ["rg", "-n", "pub fn", "src"], REPO, tail=True)
show("D rtk rg", [RTK, "rg", "-n", "pub fn", "src"], REPO, tail=True)

# E: git log --oneline
o1, e1, rc1 = run(["git", "log", "--oneline", "-40"], REPO)
o2, e2, rc2 = run([RTK, "git", "log", "--oneline", "-40"], REPO)
print(f"--- E git log --oneline -40: raw={len(o1)}B rtk={len(o2)}B rc={rc1}/{rc2}")
print(o2.decode('utf-8', 'replace')[:300])
