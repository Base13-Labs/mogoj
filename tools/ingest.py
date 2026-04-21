#!/usr/bin/env python3
"""
Mogoj Ingest — scan and import markdown files into the brain.

Commands:
  scan <directory>   Scan a directory, extract metadata, suggest keyword mappings
  import <file>      Copy a file into the appropriate docs/ or data/ location
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

    # Extract title (first # heading)
    for line in lines:
        if line.startswith("# "):
            meta["title"] = line[2:].strip()
            break

    # Detect date from filename or content
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", filepath.name)
    if date_match:
        meta["date"] = date_match.group(1)
    else:
        for line in lines[:20]:
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", line)
            if date_match:
                meta["date"] = date_match.group(1)
                break

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

    # Extract keywords from headings and bold
    kws = set()
    for match in re.finditer(r"^#{1,6}\s+(.+)$", content, re.MULTILINE):
        words = re.findall(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", match.group(1).lower())
        for w in words:
            if len(w) > 2 and w not in ("the", "and", "for", "with", "from", "that", "this"):
                kws.add(w)
    for match in re.finditer(r"\*\*([^*]+)\*\*", content):
        slug = re.sub(r"[^a-z0-9]+", "-", match.group(1).strip().lower()).strip("-")
        if slug and len(slug) > 2:
            kws.add(slug)
    meta["keywords"] = sorted(kws)[:20]  # Cap at 20

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

    # Determine destination
    if args.dest:
        dest = ROOT / args.dest
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

    # Check if destination exists
    if dest.exists() and not args.force:
        print(f"Destination already exists: {dest}")
        print("Use --force to overwrite.")
        return

    # Create parent dirs
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Copy
    shutil.copy2(src, dest)

    try:
        dest_rel = dest.relative_to(ROOT)
    except ValueError:
        dest_rel = dest

    print(f"Imported: {src.name}")
    print(f"     To: {dest_rel}")
    print(f"   Type: {meta['type']}")
    if meta["keywords"]:
        print(f"   Keywords: {', '.join(meta['keywords'][:10])}")
    print(f"\nTo index: python tools/index.py add <keyword> {dest_rel}")


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
