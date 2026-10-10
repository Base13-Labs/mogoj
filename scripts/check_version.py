#!/usr/bin/env python3
"""Verify VERSION, plugin manifests, CLI, and an optional tag agree."""

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", help="Expected release tag, including leading v")
    args = parser.parse_args()
    version = (ROOT / "VERSION").read_text().strip()
    if not re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version):
        raise SystemExit(f"VERSION is not semantic versioning: {version}")
    manifests = (
        ROOT / "plugins/mogoj/plugin.json",
        ROOT / "plugins/mogoj/.codex-plugin/plugin.json",
        ROOT / "plugins/mogoj/.claude-plugin/plugin.json",
        ROOT / "plugins/mogoj-workflows/.claude-plugin/plugin.json",
    )
    for manifest in manifests:
        found = json.loads(manifest.read_text())["version"]
        if found != version:
            raise SystemExit(f"Version mismatch: {manifest.relative_to(ROOT)} has {found}; expected {version}")
    if args.tag and args.tag != f"v{version}":
        raise SystemExit(f"Tag mismatch: {args.tag}; expected v{version}")
    print(f"Version synchronized: {version}")


if __name__ == "__main__":
    main()
