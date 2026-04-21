#!/usr/bin/env python3
"""
Mogoj Search — full-text search across brain markdown files.

Usage:
  python tools/search.py <query>
  python tools/search.py <query> --type sessions
  python tools/search.py <query> --type projects
  python tools/search.py <query> --regex
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path


def find_repo_root():
    start = Path.cwd()
    for p in [start] + list(start.parents):
        if (p / ".git").exists() or (p / "CLAUDE.md").exists():
            return p
    script = Path(__file__).resolve().parent.parent
    if (script / ".git").exists() or (script / "CLAUDE.md").exists():
        return script
    print("Error: could not find repo root.", file=sys.stderr)
    sys.exit(1)


ROOT = find_repo_root()

# Type filters map to directories
TYPE_DIRS = {
    "sessions": [ROOT / "data" / "sessions", ROOT / "docs" / "sessions"],
    "projects": [ROOT / "docs" / "projects"],
    "decisions": [ROOT / "docs" / "decisions"],
    "company": [ROOT / "docs" / "company"],
    "ram": [ROOT / "data" / "ram"],
    "imports": [ROOT / "imports"],
}

# Default: search everything
ALL_DIRS = [ROOT / "docs", ROOT / "data", ROOT / "imports"]


def collect_files(dirs):
    files = []
    for d in dirs:
        if not d.exists():
            continue
        for f in d.rglob("*.md"):
            files.append(f)
    return files


def search_file(filepath, pattern, context_lines=1):
    """Search a file for pattern matches. Returns list of (line_num, line, context_before, context_after)."""
    try:
        with open(filepath, "r", errors="replace") as f:
            lines = f.readlines()
    except (OSError, IOError):
        return []

    matches = []
    for i, line in enumerate(lines):
        if pattern.search(line):
            before = []
            after = []
            for j in range(max(0, i - context_lines), i):
                before.append((j + 1, lines[j].rstrip()))
            for j in range(i + 1, min(len(lines), i + context_lines + 1)):
                after.append((j + 1, lines[j].rstrip()))
            matches.append({
                "line_num": i + 1,
                "line": line.rstrip(),
                "before": before,
                "after": after,
            })
    return matches


def relative_path(filepath):
    try:
        return str(filepath.relative_to(ROOT))
    except ValueError:
        return str(filepath)


def main():
    parser = argparse.ArgumentParser(
        description="Full-text search across brain markdown files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python tools/search.py chatx\n"
               "  python tools/search.py 'sales sprint' --type sessions\n"
               '  python tools/search.py "dental|whatsapp" --regex\n'
               "  python tools/search.py idea --type projects --context 3\n",
    )
    parser.add_argument("query", help="Search query (plain text or regex with --regex)")
    parser.add_argument("--type", "-t", choices=list(TYPE_DIRS.keys()),
                        help="Filter to a specific doc type")
    parser.add_argument("--regex", "-r", action="store_true",
                        help="Treat query as a regex pattern")
    parser.add_argument("--context", "-C", type=int, default=1,
                        help="Lines of context around matches (default: 1)")
    parser.add_argument("--files-only", "-l", action="store_true",
                        help="Only list matching file paths")
    parser.add_argument("--case-sensitive", "-s", action="store_true",
                        help="Case-sensitive search (default: case-insensitive)")

    args = parser.parse_args()

    # Build regex pattern
    flags = 0 if args.case_sensitive else re.IGNORECASE
    try:
        if args.regex:
            pattern = re.compile(args.query, flags)
        else:
            pattern = re.compile(re.escape(args.query), flags)
    except re.error as e:
        print(f"Invalid regex: {e}", file=sys.stderr)
        sys.exit(1)

    # Collect files
    if args.type:
        dirs = TYPE_DIRS[args.type]
    else:
        dirs = ALL_DIRS
    files = collect_files(dirs)

    if not files:
        print("No markdown files found to search.")
        return

    # Search and collect results
    results = []
    for f in files:
        matches = search_file(f, pattern, args.context)
        if matches:
            results.append((f, matches))

    if not results:
        print(f"No matches for '{args.query}'.")
        return

    # Sort by match count (most matches first)
    results.sort(key=lambda x: -len(x[1]))

    total_matches = sum(len(m) for _, m in results)
    print(f"Found {total_matches} match(es) in {len(results)} file(s):\n")

    if args.files_only:
        for filepath, matches in results:
            print(f"  {relative_path(filepath)}  ({len(matches)} matches)")
        return

    for filepath, matches in results:
        rel = relative_path(filepath)
        print(f"--- {rel} ({len(matches)} match{'es' if len(matches) != 1 else ''}) ---")
        for m in matches:
            for ln, text in m["before"]:
                print(f"  {ln:4d}  {text}")
            print(f"  {m['line_num']:4d}> {m['line']}")
            for ln, text in m["after"]:
                print(f"  {ln:4d}  {text}")
            if m != matches[-1]:
                print("  ...")
        print()


if __name__ == "__main__":
    main()
