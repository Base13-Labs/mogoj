#!/usr/bin/env python3
"""Fail when release inputs contain likely private data or generated stores."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".py", ".sh", ".ps1", ".json", ".yml", ".yaml", ".ini", ".txt"}
FORBIDDEN = (
    ("absolute macOS user path", re.compile("/" + r"Users/[^/\s]+/")),
    ("legacy private brain path", re.compile("~/code/" + "brain|/code/" + "brain")),
    ("likely live token", re.compile(r"\b(?:sk-proj-|ghp_|github_pat_)[A-Za-z0-9_-]{20,}")),
    ("private key", re.compile(r"BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY")),
)
EXCLUDED = {".git", "dist", "__pycache__"}


def main():
    problems = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in EXCLUDED for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix in (".db", ".sqlite", ".zip"):
            problems.append(f"generated/private artifact: {path.relative_to(ROOT)}")
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        if path == Path(__file__).resolve() or path.name == "test_security.py":
            continue
        text = path.read_text(errors="replace")
        for label, pattern in FORBIDDEN:
            if pattern.search(text):
                problems.append(f"{label}: {path.relative_to(ROOT)}")
    if problems:
        raise SystemExit("Release audit failed:\n- " + "\n- ".join(problems))
    print("Release audit passed: no private paths, likely tokens, databases, or backups found.")


if __name__ == "__main__":
    main()
