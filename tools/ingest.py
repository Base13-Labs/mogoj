#!/usr/bin/env python3
"""
Mogoj Ingest — scan and import markdown files into the brain.

Commands:
  scan <directory>   Scan a directory, extract metadata, suggest keyword mappings
  import <file>      Copy a file into the appropriate docs/ or data/ location
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

# Import shared utilities
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    ROOT, extract_keywords, extract_title, extract_date,
    relative_path, mogoj_main, MAX_KEYWORDS_PER_DOC,
    add_root_arguments, report_root, store_path,
)


def extract_metadata(filepath):
    """Extract metadata from a markdown file."""
    meta = {
        "path": str(filepath),
        "filename": filepath.name,
        "size": filepath.stat().st_size,
        "title": None,
        "date": None,
        "type": None,
        "keywords": [],
        "frontmatter": {},
    }

    try:
        with open(filepath, "r", errors="replace") as f:
            content = f.read()
    except (OSError, IOError):
        return meta

    lines = content.split("\n")

    # Extract frontmatter
    if content.startswith("---"):
        fm_end = content.find("---", 3)
        if fm_end > 0:
            fm_text = content[3:fm_end].strip()
            for line in fm_text.split("\n"):
                if ":" in line:
                    key, val = line.split(":", 1)
                    meta["frontmatter"][key.strip()] = val.strip()

    # Extract title
    meta["title"] = extract_title(content)
    if meta["title"] == "(untitled)":
        meta["title"] = None

    # Detect date
    meta["date"] = extract_date(content, filepath.name)

    # Infer type from content signals
    content_lower = content.lower()
    if "decision" in content_lower or "decided" in content_lower or "## decision" in content_lower:
        meta["type"] = "decision"
    elif "session" in content_lower and ("## hot context" in content_lower or "## active threads" in content_lower):
        meta["type"] = "session"
    elif "## status" in content_lower or "## stack" in content_lower or "project" in (meta.get("title") or "").lower():
        meta["type"] = "project"
    elif "## team" in content_lower or "company" in content_lower:
        meta["type"] = "company"
    else:
        meta["type"] = "general"

    # Extract keywords using shared function
    kws = extract_keywords(filepath)
    meta["keywords"] = sorted(kws)[:MAX_KEYWORDS_PER_DOC]

    return meta


def suggest_destination(meta):
    """Suggest where a file should go based on its metadata."""
    t = meta.get("type", "general")
    name = meta["filename"]

    if t == "decision":
        return ROOT / "docs" / "decisions" / name
    elif t == "session":
        return ROOT / "data" / "sessions" / name
    elif t == "project":
        return ROOT / "docs" / "projects" / name
    elif t == "company":
        return ROOT / "docs" / "company" / name
    else:
        return ROOT / "docs" / name


def cmd_scan(args):
    """Scan a directory and report on its markdown files."""
    scan_dir = Path(args.directory).resolve()
    if not scan_dir.exists():
        print(f"Directory not found: {scan_dir}", file=sys.stderr)
        sys.exit(1)

    files = sorted(scan_dir.rglob("*.md"))
    if not files:
        print(f"No markdown files found in {scan_dir}")
        return

    print(f"Scanning {scan_dir} ({len(files)} markdown files):\n")

    for f in files:
        meta = extract_metadata(f)
        dest = suggest_destination(meta)

        print(f"  File:     {f.name}")
        if meta["title"]:
            print(f"  Title:    {meta['title']}")
        if meta["date"]:
            print(f"  Date:     {meta['date']}")
        print(f"  Type:     {meta['type']}")
        print(f"  Size:     {meta['size']} bytes")
        if meta["keywords"]:
            print(f"  Keywords: {', '.join(meta['keywords'][:10])}")
        try:
            dest_rel = dest.relative_to(ROOT)
        except ValueError:
            dest_rel = dest
        print(f"  Suggest:  {dest_rel}")
        print()

    if args.json:
        import json
        all_meta = [extract_metadata(f) for f in files]
        print(json.dumps(all_meta, indent=2, default=str))


def cmd_import(args):
    """Import a file into the brain."""
    src = Path(args.file).resolve()
    if not src.exists():
        print(f"File not found: {src}", file=sys.stderr)
        sys.exit(1)

    meta = extract_metadata(src)

    if args.dest:
        dest = store_path(args.dest)
    elif args.type:
        type_dirs = {
            "project": ROOT / "docs" / "projects",
            "decision": ROOT / "docs" / "decisions",
            "session": ROOT / "data" / "sessions",
            "company": ROOT / "docs" / "company",
        }
        dest_dir = type_dirs.get(args.type, ROOT / "docs")
        dest = dest_dir / src.name
    else:
        dest = suggest_destination(meta)

    if dest.exists() and not args.force:
        print(f"Destination already exists: {dest}")
        print("Use --force to overwrite.")
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)

    dest_rel = relative_path(dest)

    print(f"Imported: {src.name}")
    print(f"     To: {dest_rel}")
    print(f"   Type: {meta['type']}")
    if meta["keywords"]:
        print(f"   Keywords: {', '.join(meta['keywords'][:10])}")
    print(f"\nTo index: python tools/index.py add <keyword> {dest_rel}")


@mogoj_main
def main():
    parser = argparse.ArgumentParser(
        description="Mogoj Ingest — scan and import markdown into brain",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python tools/ingest.py scan ~/exports/\n"
               "  python tools/ingest.py scan ~/exports/ --json\n"
               "  python tools/ingest.py import ~/exports/chatx-notes.md\n"
               "  python tools/ingest.py import ~/exports/decision.md --type decision\n"
               "  python tools/ingest.py import ~/exports/doc.md --dest docs/projects/foo.md\n",
    )
    add_root_arguments(parser)
    sub = parser.add_subparsers(dest="command")

    p_scan = sub.add_parser("scan", help="Scan a directory of markdown files")
    p_scan.add_argument("directory", help="Directory to scan")
    p_scan.add_argument("--json", action="store_true", help="Output metadata as JSON")

    p_import = sub.add_parser("import", help="Import a file into the brain")
    p_import.add_argument("file", help="File to import")
    p_import.add_argument("--type", "-t", choices=["project", "decision", "session", "company"],
                          help="Override detected type")
    p_import.add_argument("--dest", "-d", help="Explicit destination path (relative to repo root)")
    p_import.add_argument("--force", "-f", action="store_true", help="Overwrite existing files")

    args = parser.parse_args()
    report_root(args)
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "scan": cmd_scan,
        "import": cmd_import,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
