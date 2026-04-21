#!/usr/bin/env python3
"""
Mogoj Index — build and query the keyword-to-doc context index.

Commands:
  build              Scan docs/ and data/sessions/, extract keywords, build context-index.json
  query <keyword>    Look up a keyword and return matching docs
  add <kw> <doc>     Add a keyword → doc mapping
  sync               Regenerate context-index.md from context-index.json
  stats              Show index statistics
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path


def find_repo_root():
    """Walk up from cwd or script dir to find the repo root (contains .git or CLAUDE.md)."""
    start = Path.cwd()
    for p in [start] + list(start.parents):
        if (p / ".git").exists() or (p / "CLAUDE.md").exists():
            return p
    # Fallback: script location
    script = Path(__file__).resolve().parent.parent
    if (script / ".git").exists() or (script / "CLAUDE.md").exists():
        return script
    print("Error: could not find repo root.", file=sys.stderr)
    sys.exit(1)


ROOT = find_repo_root()
INDEX_JSON = ROOT / "data" / "index" / "context-index.json"
INDEX_MD = ROOT / "data" / "index" / "context-index.md"

SCAN_DIRS = [
    ROOT / "docs",
    ROOT / "data" / "sessions",
]


def load_index():
    """Load the JSON index, return dict of keyword -> list of doc paths."""
    if INDEX_JSON.exists():
        with open(INDEX_JSON, "r") as f:
            return json.load(f)
    return {}


def save_index(index):
    """Save the JSON index."""
    INDEX_JSON.parent.mkdir(parents=True, exist_ok=True)
    # Sort keys for deterministic output
    sorted_index = dict(sorted(index.items()))
    for k in sorted_index:
        sorted_index[k] = sorted(set(sorted_index[k]))
    with open(INDEX_JSON, "w") as f:
        json.dump(sorted_index, f, indent=2)


def relative_doc_path(filepath):
    """Return a doc path relative to the repo root's docs/ or data/ parent, matching index format."""
    fp = Path(filepath).resolve()
    # Try relative to ROOT/docs first
    try:
        rel = fp.relative_to(ROOT / "docs")
        return str(rel)
    except ValueError:
        pass
    # Try relative to ROOT/data
    try:
        rel = fp.relative_to(ROOT / "data")
        return str(rel)
    except ValueError:
        pass
    # Try relative to ROOT
    try:
        return str(fp.relative_to(ROOT))
    except ValueError:
        return str(fp)


def extract_keywords(filepath):
    """Extract keywords from a markdown file: headings, bold terms, frontmatter tags."""
    keywords = set()
    try:
        with open(filepath, "r", errors="replace") as f:
            content = f.read()
    except (OSError, IOError):
        return keywords

    # Extract from headings (# Heading Text)
    for match in re.finditer(r"^#{1,6}\s+(.+)$", content, re.MULTILINE):
        heading = match.group(1).strip()
        # Skip generic headings
        if heading.lower() in ("summary", "overview", "notes", "context", "details",
                                "background", "references", "links", "appendix"):
            continue
        # Slugify heading into keywords
        words = re.findall(r"[a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)*", heading.lower())
        for w in words:
            if len(w) > 2 and w not in ("the", "and", "for", "with", "from", "that", "this", "are", "was", "has", "have"):
                keywords.add(w)

    # Extract bold terms (**term**)
    for match in re.finditer(r"\*\*([^*]+)\*\*", content):
        term = match.group(1).strip().lower()
        # Slugify
        slug = re.sub(r"[^a-z0-9]+", "-", term).strip("-")
        if slug and len(slug) > 2:
            keywords.add(slug)
        # Also add individual words if multi-word
        words = re.findall(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", term)
        for w in words:
            if len(w) > 2 and w not in ("the", "and", "for", "with", "from", "that", "this", "are", "was", "has", "have"):
                keywords.add(w)

    # Extract frontmatter tags (tags: [a, b, c] or keywords: ...)
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if fm_match:
        fm = fm_match.group(1)
        for line in fm.split("\n"):
            if re.match(r"(tags|keywords)\s*:", line, re.IGNORECASE):
                vals = re.findall(r"[a-zA-Z0-9][-a-zA-Z0-9_]*", line.split(":", 1)[1])
                for v in vals:
                    v = v.lower()
                    if len(v) > 2:
                        keywords.add(v)

    return keywords


def collect_md_files():
    """Collect all .md files from scan directories."""
    files = []
    for d in SCAN_DIRS:
        if not d.exists():
            continue
        for f in d.rglob("*.md"):
            files.append(f)
    return files


def cmd_build(args):
    """Build context-index.json by scanning markdown files."""
    index = load_index() if args.merge else {}
    files = collect_md_files()

    if not files:
        print("No markdown files found to scan.")
        return

    new_entries = 0
    for f in files:
        doc_path = relative_doc_path(f)
        kws = extract_keywords(f)
        for kw in kws:
            if kw not in index:
                index[kw] = []
            if doc_path not in index[kw]:
                index[kw].append(doc_path)
                new_entries += 1

    save_index(index)
    print(f"Scanned {len(files)} files.")
    print(f"Index now has {len(index)} keywords.")
    print(f"Added {new_entries} new keyword-doc mappings.")
    print(f"Saved to {INDEX_JSON}")

    if args.sync:
        sync_to_md(index)


def cmd_query(args):
    """Look up a keyword in the index."""
    index = load_index()
    keyword = args.keyword.lower().strip()

    if not index:
        print("Index is empty. Run 'build' first.")
        return

    # Exact match
    if keyword in index:
        docs = index[keyword]
        print(f"'{keyword}' -> {len(docs)} doc(s):")
        for d in docs:
            print(f"  - {d}")
        return

    # Fuzzy: find keywords containing the query
    matches = {k: v for k, v in index.items() if keyword in k}
    if matches:
        print(f"No exact match for '{keyword}'. Partial matches:")
        for k, docs in sorted(matches.items()):
            print(f"\n  '{k}' -> {len(docs)} doc(s):")
            for d in docs:
                print(f"    - {d}")
    else:
        print(f"No matches for '{keyword}'.")


def cmd_add(args):
    """Add a keyword -> doc mapping."""
    index = load_index()
    kw = args.keyword.lower().strip()
    doc = args.doc_path.strip()

    if kw not in index:
        index[kw] = []
    if doc not in index[kw]:
        index[kw].append(doc)
        save_index(index)
        print(f"Added: '{kw}' -> {doc}")
    else:
        print(f"Mapping already exists: '{kw}' -> {doc}")


def sync_to_md(index=None):
    """Regenerate context-index.md from context-index.json."""
    if index is None:
        index = load_index()

    if not index:
        print("Index is empty. Nothing to sync.")
        return

    # Group by first letter
    by_letter = defaultdict(list)
    for kw in sorted(index.keys()):
        letter = kw[0].upper()
        if not letter.isalpha():
            letter = "#"
        by_letter[letter].append(kw)

    lines = [
        "# Context Index",
        "",
        "Multi-keyword -> doc mapping. Multiple keywords point to same doc. "
        "Look up any keyword, find all related conversations, decisions, and docs.",
        "",
        '**How to use:** Search keyword -> get doc list -> read hot (direct) refs first '
        '-> follow warm (second-degree) refs if needed.',
        "",
        '**Update rule:** Every `/b13-save` appends new keywords here. '
        'Never remove old entries -- mark `[archived]` if obsolete.',
        "",
        "---",
        "",
    ]

    for letter in sorted(by_letter.keys()):
        lines.append(f"## {letter}")
        lines.append("")
        for kw in by_letter[letter]:
            docs = ", ".join(index[kw])
            lines.append(f"- **{kw}**: {docs}")
        lines.append("")

    INDEX_MD.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_MD, "w") as f:
        f.write("\n".join(lines))

    print(f"Synced {len(index)} keywords to {INDEX_MD}")


def cmd_sync(args):
    sync_to_md()


def cmd_stats(args):
    """Show index statistics."""
    index = load_index()
    if not index:
        print("Index is empty.")
        return

    total_kw = len(index)
    all_docs = set()
    doc_count = defaultdict(int)
    for kw, docs in index.items():
        for d in docs:
            all_docs.add(d)
            doc_count[d] += 1

    print(f"Total keywords:  {total_kw}")
    print(f"Total docs:      {len(all_docs)}")
    print(f"Total mappings:  {sum(len(v) for v in index.values())}")

    if doc_count:
        print(f"\nMost connected docs (by keyword count):")
        for doc, count in sorted(doc_count.items(), key=lambda x: -x[1])[:10]:
            print(f"  {count:3d}  {doc}")


def main():
    parser = argparse.ArgumentParser(
        description="Mogoj Index — keyword-to-doc context index manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python tools/index.py build\n"
               "  python tools/index.py build --merge\n"
               "  python tools/index.py query chatx\n"
               "  python tools/index.py add sales-sprint decisions/my-doc.md\n"
               "  python tools/index.py sync\n"
               "  python tools/index.py stats\n",
    )
    sub = parser.add_subparsers(dest="command")

    p_build = sub.add_parser("build", help="Scan docs and build context-index.json")
    p_build.add_argument("--merge", action="store_true", help="Merge with existing index instead of replacing")
    p_build.add_argument("--sync", action="store_true", help="Also regenerate context-index.md after build")

    p_query = sub.add_parser("query", help="Look up a keyword in the index")
    p_query.add_argument("keyword", help="Keyword to search for")

    p_add = sub.add_parser("add", help="Add a keyword -> doc mapping")
    p_add.add_argument("keyword", help="Keyword to add")
    p_add.add_argument("doc_path", help="Doc path to map to")

    sub.add_parser("sync", help="Regenerate context-index.md from context-index.json")
    sub.add_parser("stats", help="Show index statistics")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "build": cmd_build,
        "query": cmd_query,
        "add": cmd_add,
        "sync": cmd_sync,
        "stats": cmd_stats,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
