#!/usr/bin/env python3
"""
Mogoj RAM — manage the active session memory (data/ram/current.md).

Commands:
  status          Show current RAM contents summary
  clear           Clear current.md to empty template
  archive <name>  Move current.md to data/ram/archive/<name>.md
  list            List all archived RAMs
  load <name>     Load an archived RAM as current
"""

import argparse
import os
import re
import shutil
import sys
from datetime import date
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
RAM_DIR = ROOT / "data" / "ram"
CURRENT = RAM_DIR / "current.md"
ARCHIVE_DIR = RAM_DIR / "archive"

EMPTY_TEMPLATE = f"""# RAM — Active Session Memory

**Session**: {date.today().isoformat()} — (new session)
**Status**: Active

---

## Hot Context (direct — read these first)

(none yet)

## Warm Context (second-degree — follow if needed)

(none yet)

## Active Threads

(none yet)

## Key Facts This Session

(none yet)

## Unresolved

(none yet)
"""


def cmd_status(args):
    """Show current RAM summary."""
    if not CURRENT.exists():
        print("No active RAM (data/ram/current.md does not exist).")
        return

    with open(CURRENT, "r", errors="replace") as f:
        content = f.read()

    lines = content.strip().split("\n")
    total_lines = len(lines)

    # Extract session line
    session = "(unknown)"
    status = "(unknown)"
    for line in lines[:10]:
        if line.startswith("**Session**:"):
            session = line.split(":", 1)[1].strip().strip("*")
        elif line.startswith("**Status**:"):
            status = line.split(":", 1)[1].strip().strip("*")

    # Count sections and items
    sections = [l for l in lines if l.startswith("## ")]
    bullet_items = [l for l in lines if re.match(r"^\s*[-*]\s+", l) or re.match(r"^\s*\d+\.\s+", l)]

    # Count hot and warm refs
    hot_refs = 0
    warm_refs = 0
    in_hot = False
    in_warm = False
    for line in lines:
        if "Hot Context" in line:
            in_hot = True
            in_warm = False
        elif "Warm Context" in line:
            in_hot = False
            in_warm = True
        elif line.startswith("## "):
            in_hot = False
            in_warm = False
        elif re.match(r"^\s*-\s+", line):
            if in_hot:
                hot_refs += 1
            elif in_warm:
                warm_refs += 1

    print(f"Session:     {session}")
    print(f"Status:      {status}")
    print(f"Lines:       {total_lines}")
    print(f"Sections:    {len(sections)}")
    print(f"Items:       {len(bullet_items)}")
    print(f"Hot refs:    {hot_refs}")
    print(f"Warm refs:   {warm_refs}")


def cmd_clear(args):
    """Clear current.md to empty template."""
    if CURRENT.exists() and not args.force:
        print("Current RAM exists. Use --force to overwrite, or 'archive' it first.")
        return

    RAM_DIR.mkdir(parents=True, exist_ok=True)
    with open(CURRENT, "w") as f:
        f.write(EMPTY_TEMPLATE)
    print(f"RAM cleared: {CURRENT}")


def cmd_archive(args):
    """Archive current.md."""
    if not CURRENT.exists():
        print("No current RAM to archive.")
        return

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    name = args.name
    if not name.endswith(".md"):
        name += ".md"
    dest = ARCHIVE_DIR / name

    if dest.exists() and not args.force:
        print(f"Archive '{name}' already exists. Use --force to overwrite.")
        return

    shutil.copy2(CURRENT, dest)
    print(f"Archived: {CURRENT} -> {dest}")

    if args.clear:
        with open(CURRENT, "w") as f:
            f.write(EMPTY_TEMPLATE)
        print("RAM cleared to empty template.")


def cmd_list(args):
    """List archived RAMs."""
    if not ARCHIVE_DIR.exists():
        print("No archive directory yet.")
        return

    archives = sorted(ARCHIVE_DIR.glob("*.md"))
    if not archives:
        print("No archived RAMs.")
        return

    print(f"Archived RAMs ({len(archives)}):\n")
    for a in archives:
        size = a.stat().st_size
        # Try to extract session line
        session = ""
        try:
            with open(a, "r", errors="replace") as f:
                for line in f:
                    if line.startswith("**Session**:"):
                        session = line.split(":", 1)[1].strip().strip("*").strip()
                        break
        except (OSError, IOError):
            pass
        name = a.stem
        print(f"  {name:<40s}  {size:>6d}B  {session}")


def cmd_load(args):
    """Load an archived RAM as current."""
    name = args.name
    if not name.endswith(".md"):
        name += ".md"
    src = ARCHIVE_DIR / name

    if not src.exists():
        print(f"Archive '{name}' not found.")
        # Suggest available archives
        if ARCHIVE_DIR.exists():
            available = [a.stem for a in ARCHIVE_DIR.glob("*.md")]
            if available:
                print(f"Available: {', '.join(available)}")
        return

    if CURRENT.exists() and not args.force:
        print("Current RAM exists. Use --force to overwrite, or 'archive' it first.")
        return

    RAM_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, CURRENT)
    print(f"Loaded: {src} -> {CURRENT}")


def main():
    parser = argparse.ArgumentParser(
        description="Mogoj RAM — manage active session memory",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python tools/ram.py status\n"
               "  python tools/ram.py archive 2026-04-19-focus-session\n"
               "  python tools/ram.py archive 2026-04-19-focus-session --clear\n"
               "  python tools/ram.py list\n"
               "  python tools/ram.py load 2026-04-19-focus-session\n"
               "  python tools/ram.py clear --force\n",
    )
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show current RAM contents summary")

    p_clear = sub.add_parser("clear", help="Clear current.md to empty template")
    p_clear.add_argument("--force", "-f", action="store_true", help="Overwrite without prompt")

    p_archive = sub.add_parser("archive", help="Archive current.md")
    p_archive.add_argument("name", help="Archive name (e.g., 2026-04-19-session)")
    p_archive.add_argument("--force", "-f", action="store_true", help="Overwrite existing archive")
    p_archive.add_argument("--clear", "-c", action="store_true", help="Clear RAM after archiving")

    p_list = sub.add_parser("list", help="List archived RAMs")

    p_load = sub.add_parser("load", help="Load an archived RAM as current")
    p_load.add_argument("name", help="Archive name to load")
    p_load.add_argument("--force", "-f", action="store_true", help="Overwrite current RAM")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "status": cmd_status,
        "clear": cmd_clear,
        "archive": cmd_archive,
        "list": cmd_list,
        "load": cmd_load,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
