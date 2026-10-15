#!/usr/bin/env python3
"""Synchronize the self-contained Codex plugin runtime from canonical sources."""

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "mogoj"
TOP_LEVEL = ("VERSION", "config.ini.example")


def pairs():
    yield from ((ROOT / name, PLUGIN / name) for name in TOP_LEVEL)
    for source in sorted((ROOT / "tools").iterdir()):
        if source.is_file() and source.suffix in {".py", ".txt"}:
            yield source, PLUGIN / "tools" / source.name


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    drift = []
    for source, target in pairs():
        if not target.is_file() or target.read_bytes() != source.read_bytes():
            drift.append(target.relative_to(ROOT).as_posix())
            if not args.check:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
    if drift and args.check:
        raise SystemExit("Codex runtime is out of sync:\n- " + "\n- ".join(drift))
    print("Codex runtime synchronized." if drift else "Codex runtime already synchronized.")


if __name__ == "__main__":
    main()
