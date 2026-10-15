#!/usr/bin/env python3
"""Build a deterministic, self-contained Codex desktop plugin ZIP."""

import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "mogoj"
DIST = ROOT / "dist"
VERSION = (ROOT / "VERSION").read_text().strip()
ARCHIVE = DIST / f"mogoj-codex-{VERSION}.zip"
EXCLUDED = {".claude-plugin", "__pycache__"}


def files():
    return [
        path for path in sorted(PLUGIN.rglob("*"))
        if path.is_file()
        and not any(part in EXCLUDED for part in path.relative_to(PLUGIN).parts)
        and path.relative_to(PLUGIN).as_posix() != "hooks/claude-hooks.json"
        and path.suffix != ".pyc"
    ]


def main():
    subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "sync_codex_runtime.py"), "--check"],
        check=True,
        stdout=subprocess.PIPE,
    )
    DIST.mkdir(exist_ok=True)
    with zipfile.ZipFile(ARCHIVE, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as package:
        for path in files():
            info = zipfile.ZipInfo(
                f"mogoj/{path.relative_to(PLUGIN).as_posix()}",
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (path.stat().st_mode & 0xFFFF) << 16
            package.writestr(info, path.read_bytes())
    digest = hashlib.sha256(ARCHIVE.read_bytes()).hexdigest()
    checksum = DIST / f"{ARCHIVE.name}.sha256"
    checksum.write_text(f"{digest}  {ARCHIVE.name}\n")
    print(f"{ARCHIVE.name}  {ARCHIVE.stat().st_size} bytes")
    print(checksum.name)


if __name__ == "__main__":
    main()
