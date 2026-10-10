#!/usr/bin/env python3
"""
Mogoj RAM — manage the active session memory (data/ram/current.md).

Commands:
  status          Show current RAM contents summary
  clear           Clear current.md to empty template
  archive <name>  Move current.md to data/ram/archive/<name>.md
  list            List all archived RAMs
  load <name>     Load an archived RAM as current
  refresh         Generate compact pointer-based RAM (supports --auto)
"""

import argparse
import re
import shutil
import sys
from datetime import date
from pathlib import Path

# Import shared utilities
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    RAM_DIR, CURRENT_RAM as CURRENT, ARCHIVE_DIR,
    mogoj_main,
)


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


def _has_real_content(filepath):
    """Check if RAM file has real content (not just empty template or placeholders)."""
    if not filepath.exists():
        return False
    with open(filepath, "r", errors="replace") as f:
        content = f.read()
    # Check if all sections are just placeholders
    stripped = content.strip()
    if not stripped or "(none yet)" in stripped and "(agent fills" not in stripped:
        # All placeholder — likely empty template
        placeholder_lines = [l for l in stripped.split("\n")
                           if l.strip() and not l.startswith("#") and not l.startswith("**")
                           and not l.startswith("---") and not l.startswith("-")]
        real_lines = [l for l in placeholder_lines
                     if l.strip() not in ("(none yet)", "(agent fills from conversation)")]
        return len(real_lines) > 0
    return True


def _auto_archive_current():
    """Archive current RAM before overwriting, if it has real content."""
    if not CURRENT.exists():
        return
    if not _has_real_content(CURRENT):
        return

    # Extract date and topic from current RAM for archive name
    archive_name = "unknown"
    with open(CURRENT, "r", errors="replace") as f:
        for line in f:
            if line.startswith("**Session**:"):
                session_info = line.split(":", 1)[1].strip().strip("*").strip()
                # Try to build a clean archive name from session info
                archive_name = re.sub(r"[^a-z0-9-]+", "-", session_info.lower()).strip("-")[:60]
                break

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    dest = ARCHIVE_DIR / f"{archive_name}.md"

    # Avoid overwriting existing archives
    counter = 1
    while dest.exists():
        dest = ARCHIVE_DIR / f"{archive_name}-{counter}.md"
        counter += 1

    shutil.copy2(CURRENT, dest)
    print(f"Auto-archived: {dest.name}")


def cmd_status(args):
    """Show current RAM summary."""
    if not CURRENT.exists():
        print("No active RAM (data/ram/current.md does not exist).")
        return

    with open(CURRENT, "r", errors="replace") as f:
        content = f.read()

    lines = content.strip().split("\n")
    total_lines = len(lines)

    session = "(unknown)"
    status = "(unknown)"
    for line in lines[:10]:
        if line.startswith("**Session**:"):
            session = line.split(":", 1)[1].strip().strip("*")
        elif line.startswith("**Status**:"):
            status = line.split(":", 1)[1].strip().strip("*")

    sections = [l for l in lines if l.startswith("## ")]
    bullet_items = [l for l in lines if re.match(r"^\s*[-*]\s+", l) or re.match(r"^\s*\d+\.\s+", l)]

    hot_refs = 0
    warm_refs = 0
    in_hot = False
    in_warm = False
    for line in lines:
        if "Hot Context" in line or line.strip() == "## Hot":
            in_hot = True
            in_warm = False
        elif "Warm Context" in line or line.strip() == "## Warm":
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


def _parse_session_sections(session_path):
    """Parse a session doc to extract Threads, Facts, and Open items."""
    threads = []
    facts = []
    open_items = []

    try:
        with open(session_path, "r", errors="replace") as f:
            content = f.read()
    except (OSError, IOError):
        return threads, facts, open_items

    lines = content.split("\n")
    current_section = None

    for line in lines:
        stripped = line.strip()

        # Detect sections
        if re.match(r"^##\s+", stripped):
            heading = stripped.lstrip("#").strip().lower()
            if "key point" in heading or "active thread" in heading:
                current_section = "threads"
            elif "decision" in heading:
                current_section = "facts"
            elif "open question" in heading or "next step" in heading or "unresolved" in heading:
                current_section = "open"
            else:
                current_section = None
            continue

        # Collect bullet points from relevant sections
        bullet_match = re.match(r"^\s*[-*]\s+(.+)", stripped)
        if not bullet_match:
            continue

        item = bullet_match.group(1).strip()
        if not item or item in ("(none yet)", "(agent fills from conversation)"):
            continue

        # Truncate long items
        if len(item) > 120:
            item = item[:117] + "..."

        if current_section == "threads":
            threads.append(item)
        elif current_section == "facts":
            facts.append(item)
        elif current_section == "open":
            open_items.append(item)

    return threads, facts, open_items


def cmd_refresh(args):
    """Generate compact pointer-based RAM for lite continuation."""
    session_path = args.session or "(no session)"
    session_hash = args.hash or "--------"
    summary = args.summary or "(no summary)"
    fingerprint = args.fingerprint or "------------ 0 0"
    mode = args.mode or "lite"
    session_date = args.date or date.today().isoformat()
    topic = args.topic or "(unknown)"

    hot_refs = [r.strip() for r in (args.hot or "").split(",") if r.strip()]
    warm_refs = [r.strip() for r in (args.warm or "").split(",") if r.strip()]

    # Auto-archive previous RAM before overwriting
    _auto_archive_current()

    # Auto-extract sections from session doc if --auto flag set
    auto_threads, auto_facts, auto_open = [], [], []
    if args.auto and args.session:
        session_file = Path(args.session)
        if not session_file.is_absolute():
            from common import ROOT
            session_file = ROOT / session_file
        if session_file.exists():
            auto_threads, auto_facts, auto_open = _parse_session_sections(session_file)

    lines = [
        "# RAM — Compressed",
        "",
        f"**Session**: {session_date} — {topic}",
        f"**Mode**: {mode}",
        f"**Index**: {fingerprint}",
        "",
        "---",
        "",
        "## Pointers",
        f"- `{session_path}` [{session_hash}] — {summary}",
        "",
    ]

    if hot_refs:
        lines.append("## Hot")
        for ref in hot_refs:
            lines.append(f"- `{ref}`")
        lines.append("")

    if warm_refs:
        lines.append("## Warm")
        for ref in warm_refs:
            lines.append(f"- `{ref}`")
        lines.append("")

    # Threads section
    lines.append("## Threads")
    lines.append("")
    if auto_threads:
        for t in auto_threads[:8]:
            lines.append(f"- {t}")
    else:
        lines.append("(agent fills from conversation)")
    lines.append("")

    # Facts section
    lines.append("## Facts")
    lines.append("")
    if auto_facts:
        for f_item in auto_facts[:8]:
            lines.append(f"- {f_item}")
    else:
        lines.append("(agent fills from conversation)")
    lines.append("")

    # Open section
    lines.append("## Open")
    lines.append("")
    if auto_open:
        for o in auto_open[:5]:
            lines.append(f"- {o}")
    else:
        lines.append("(agent fills from conversation)")
    lines.append("")

    RAM_DIR.mkdir(parents=True, exist_ok=True)
    with open(CURRENT, "w") as f:
        f.write("\n".join(lines))

    line_count = len(lines)
    byte_count = sum(len(l) + 1 for l in lines)
    print(f"RAM refreshed: {CURRENT}")
    print(f"Mode: {mode} | Lines: {line_count} | Bytes: {byte_count}")
    if args.auto:
        print(f"Auto-filled: {len(auto_threads)} threads, {len(auto_facts)} facts, {len(auto_open)} open")


def cmd_load(args):
    """Load an archived RAM as current."""
    name = args.name
    if not name.endswith(".md"):
        name += ".md"
    src = ARCHIVE_DIR / name

    if not src.exists():
        print(f"Archive '{name}' not found.")
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


@mogoj_main
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
               "  python tools/ram.py clear --force\n"
               "  python tools/ram.py refresh --session path --auto\n",
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

    p_refresh = sub.add_parser("refresh", help="Generate compact pointer-based RAM")
    p_refresh.add_argument("--session", help="Session doc path")
    p_refresh.add_argument("--hash", help="Session doc SHA-256 prefix")
    p_refresh.add_argument("--summary", help="One-line session summary")
    p_refresh.add_argument("--fingerprint", help="Index fingerprint string")
    p_refresh.add_argument("--mode", default="lite", choices=["lite", "full"], help="RAM mode")
    p_refresh.add_argument("--date", help="Session date (YYYY-MM-DD)")
    p_refresh.add_argument("--topic", help="Session topic slug")
    p_refresh.add_argument("--hot", help="Comma-separated hot ref paths")
    p_refresh.add_argument("--warm", help="Comma-separated warm ref paths")
    p_refresh.add_argument("--auto", action="store_true",
                          help="Auto-extract Threads/Facts/Open from session doc")

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
        "refresh": cmd_refresh,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
