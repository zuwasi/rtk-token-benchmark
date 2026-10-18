"""Builds fixes/rtk-lint-script-fix.zip from fixes/rtk-lint-script-fix/.

Uses fixed timestamps so rebuilding unchanged files gives an identical zip, and marks
the .sh scripts executable for people who unzip on macOS or Linux.
"""
import pathlib
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE / "rtk-lint-script-fix"
OUT = HERE / "rtk-lint-script-fix.zip"
STAMP = (2026, 10, 18, 0, 0, 0)

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(SRC.rglob("*")):
        if not path.is_file():
            continue
        info = zipfile.ZipInfo(f"{SRC.name}/{path.relative_to(SRC).as_posix()}", STAMP)
        mode = 0o755 if path.suffix == ".sh" else 0o644
        info.create_system = 3  # Unix; unzip ignores permission bits on DOS-made entries
        info.external_attr = (0o100000 | mode) << 16
        info.compress_type = zipfile.ZIP_DEFLATED
        zf.writestr(info, path.read_bytes())

with zipfile.ZipFile(OUT) as zf:
    for i in zf.infolist():
        print(f"{oct(i.external_attr >> 16 & 0o777)}  {i.file_size:>6}  {i.filename}")
print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
