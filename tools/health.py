#!/usr/bin/env python3
"""
Mogoj Health — memory system health checks and diagnostics.

Commands:
  check [--fix]    Run all checks, optionally auto-fix safe issues
  stale            Show docs not updated in N days (default: 30)
  orphans          Keywords pointing to non-existent docs
  duplicates       Duplicate keyword mappings
  refs             Broken markdown cross-references
  people           Names in sessions but missing docs/people/ profiles
"""

import argparse
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Import shared utilities
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    ROOT, INDEX_JSON, DB_PATH, CURRENT_RAM,
    load_json, save_json, mogoj_main, add_root_arguments, report_root,
)


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_orphans(index, fix=False):
    """Find keywords pointing to docs that don't exist on disk."""
    issues = []
    fixed = 0

    for kw, doc_paths in list(index.items()):
        for doc in list(doc_paths):
            # Check multiple possible locations
            candidates = [
                ROOT / "docs" / doc,
                ROOT / "data" / doc,
                ROOT / doc,
            ]
            if not any(c.exists() for c in candidates):
                issues.append((kw, doc))
                if fix:
                    doc_paths.remove(doc)
                    fixed += 1

        # Remove keyword if no docs remain
        if fix and not index[kw]:
            del index[kw]

    return issues, fixed


def check_duplicates(index, fix=False):
    """Find duplicate keyword->doc mappings."""
    issues = []
    fixed = 0

    for kw, doc_paths in index.items():
        seen = set()
        unique = []
        for doc in doc_paths:
            if doc in seen:
                issues.append((kw, doc))
                fixed += 1
            else:
                seen.add(doc)
                unique.append(doc)
        if fix:
            index[kw] = unique

    return issues, fixed


def check_stale(days=30):
    """Find docs not modified in N days."""
    stale = []
    cutoff = datetime.now().timestamp() - (days * 86400)

    for d in [ROOT / "docs", ROOT / "data" / "sessions"]:
        if not d.exists():
            continue
        for f in d.rglob("*.md"):
            if f.stat().st_mtime < cutoff:
                age = (datetime.now().timestamp() - f.stat().st_mtime) / 86400
                try:
                    rel = str(f.relative_to(ROOT))
                except ValueError:
                    rel = str(f)
                stale.append((rel, int(age)))

    return sorted(stale, key=lambda x: -x[1])


def check_broken_refs():
    """Find broken markdown cross-references in docs."""
    broken = []
    link_pattern = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")

    for d in [ROOT / "docs", ROOT / "data"]:
        if not d.exists():
            continue
        for f in d.rglob("*.md"):
            try:
                with open(f, "r", errors="replace") as fh:
                    content = fh.read()
            except (OSError, IOError):
                continue

            for match in link_pattern.finditer(content):
                target = match.group(2)
                # Skip URLs, anchors, and mailto
                if target.startswith(("http", "#", "mailto:")):
                    continue
                # Strip anchor fragments (e.g., path.md#L68)
                target_clean = target.split("#")[0]
                if not target_clean:
                    continue
                # Resolve relative to file's directory
                target_path = (f.parent / target_clean).resolve()
                if not target_path.exists():
                    try:
                        src_rel = str(f.relative_to(ROOT))
                    except ValueError:
                        src_rel = str(f)
                    broken.append((src_rel, target, match.group(1)))

    return broken


def check_missing_people():
    """Find person names mentioned in sessions but missing profiles."""
    people_dir = ROOT / "docs" / "people"
    existing = set()
    if people_dir.exists():
        for f in people_dir.glob("*.md"):
            existing.add(f.stem.lower())

    # Patterns that suggest a person is being mentioned
    # "DJ said", "Tarango suggested", "spoke with X", etc.
    name_patterns = [
        re.compile(r"\b([A-Z][a-z]{2,15})\s+(?:said|suggested|mentioned|asked|wants|thinks|agreed|disagreed|proposed|noted|confirmed)", re.MULTILINE),
        re.compile(r"(?:spoke with|met with|call with|sync with|hired|onboard(?:ing|ed)?)\s+\*?\*?([A-Z][a-z]{2,15})", re.MULTILINE),
    ]

    # Common false positives
    skip_names = {
        "claude", "codex", "react", "python", "supabase", "stripe", "vercel",
        "tauri", "whatsapp", "openai", "anthropic", "google", "apple", "meta",
        "github", "linear", "slack", "figma", "notion", "base", "this", "that",
        "the", "sessions", "decisions", "projects", "company", "user",
    }

    mentions = {}  # name -> count
    sessions_dir = ROOT / "data" / "sessions"
    if not sessions_dir.exists():
        return []

    for f in sessions_dir.rglob("*.md"):
        try:
            with open(f, "r", errors="replace") as fh:
                content = fh.read()
        except (OSError, IOError):
            continue

        for pattern in name_patterns:
            for match in pattern.finditer(content):
                name = match.group(1)
                name_lower = name.lower()
                if name_lower in skip_names or name_lower in existing:
                    continue
                if len(name) < 3:
                    continue
                mentions[name] = mentions.get(name, 0) + 1

    # Only report names mentioned 2+ times
    return sorted(
        [(name, count) for name, count in mentions.items() if count >= 2],
        key=lambda x: -x[1]
    )


def check_ram_placeholders():
    """Check if RAM has unfilled placeholder sections."""
    if not CURRENT_RAM.exists():
        return []

    issues = []
    with open(CURRENT_RAM, "r", errors="replace") as f:
        content = f.read()

    if "(agent fills from conversation)" in content:
        issues.append("RAM has unfilled placeholder sections")
    if "(none yet)" in content and "## Hot" not in content:
        issues.append("RAM is still on empty template")

    return issues


def check_index_db_drift():
    """Check if JSON index and SQLite DB are in sync."""
    if not DB_PATH.exists():
        return [("DB not initialized", "Run: python3 tools/db.py init && python3 tools/db.py sync")]

    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))

    index = load_json(INDEX_JSON) or {}
    json_kw_count = len(index)
    json_doc_count = len(set(d for docs in index.values() for d in docs))

    db_kw_count = conn.execute("SELECT COUNT(DISTINCT keyword) FROM keywords").fetchone()[0]
    db_doc_count = conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0]

    conn.close()

    issues = []
    if abs(json_kw_count - db_kw_count) > 5:
        issues.append((f"Keyword drift: JSON={json_kw_count}, DB={db_kw_count}",
                       "Run: python3 tools/db.py sync"))
    if abs(json_doc_count - db_doc_count) > 5:
        issues.append((f"Doc drift: JSON refs {json_doc_count}, DB has {db_doc_count}",
                       "Run: python3 tools/db.py sync"))

    return issues


# ---------------------------------------------------------------------------
# Main check command
# ---------------------------------------------------------------------------

def cmd_check(args):
    """Run all health checks."""
    fix = args.fix
    index = load_json(INDEX_JSON) or {}
    modified = False

    print("SupaMogoJ Health Report")
    print("=" * 40)
    print()

    issues_total = 0

    # 1. Orphan keywords
    orphans, orphan_fixed = check_orphans(index, fix=fix)
    if orphans:
        issues_total += len(orphans)
        status = f"FIXED {orphan_fixed}" if fix else "WARN"
        print(f"[{status}] {len(orphans)} orphan keyword(s)")
        for kw, doc in orphans[:5]:
            print(f"  '{kw}' -> {doc}")
        if len(orphans) > 5:
            print(f"  ... and {len(orphans) - 5} more")
        if not fix:
            print("  Fix: python3 tools/health.py check --fix")
        modified = modified or (fix and orphan_fixed > 0)
    else:
        print("[OK] No orphan keywords")

    # 2. Duplicates
    dupes, dupe_fixed = check_duplicates(index, fix=fix)
    if dupes:
        issues_total += len(dupes)
        status = f"FIXED {dupe_fixed}" if fix else "WARN"
        print(f"[{status}] {len(dupes)} duplicate mapping(s)")
        modified = modified or (fix and dupe_fixed > 0)
    else:
        print("[OK] No duplicate mappings")

    # 3. Stale docs
    stale = check_stale(days=30)
    if stale:
        issues_total += len(stale)
        print(f"[INFO] {len(stale)} doc(s) not updated in 30+ days")
        for path, age in stale[:5]:
            print(f"  {age}d  {path}")
        if len(stale) > 5:
            print(f"  ... and {len(stale) - 5} more")
    else:
        print("[OK] All docs recently updated")

    # 4. Broken refs
    broken = check_broken_refs()
    if broken:
        issues_total += len(broken)
        print(f"[WARN] {len(broken)} broken cross-reference(s)")
        for src, target, text in broken[:5]:
            print(f"  {src}: [{text}]({target})")
    else:
        print("[OK] No broken cross-references")

    # 5. Missing people
    missing_people = check_missing_people()
    if missing_people:
        issues_total += len(missing_people)
        print(f"[INFO] {len(missing_people)} person(s) mentioned but no profile")
        for name, count in missing_people:
            print(f"  {name} (mentioned {count}x)")
        print("  Create: docs/people/{name}.md")
    else:
        print("[OK] All mentioned people have profiles")

    # 6. RAM placeholders
    ram_issues = check_ram_placeholders()
    if ram_issues:
        issues_total += len(ram_issues)
        for issue in ram_issues:
            print(f"[INFO] {issue}")
    else:
        print("[OK] RAM is populated")

    # 7. Index/DB drift
    drift = check_index_db_drift()
    if drift:
        for msg, fix_cmd in drift:
            issues_total += 1
            print(f"[WARN] {msg}")
            print(f"  Fix: {fix_cmd}")
    else:
        print("[OK] Index and DB in sync")

    print()
    if issues_total == 0:
        print("Status: All clean")
    else:
        print(f"Status: {issues_total} issue(s) found")

    # Save index if modified
    if modified:
        sorted_index = dict(sorted(index.items()))
        for k in sorted_index:
            sorted_index[k] = sorted(set(sorted_index[k]))
        save_json(INDEX_JSON, sorted_index, sort_keys=False)
        print(f"\nIndex updated and saved.")


def cmd_stale(args):
    """Show stale documents."""
    stale = check_stale(days=args.days)
    if not stale:
        print(f"No docs older than {args.days} days.")
        return
    print(f"Docs not updated in {args.days}+ days:\n")
    for path, age in stale:
        print(f"  {age:>4d}d  {path}")


def cmd_orphans(args):
    """Show orphan keywords."""
    index = load_json(INDEX_JSON) or {}
    orphans, _ = check_orphans(index)
    if not orphans:
        print("No orphan keywords.")
        return
    print(f"Orphan keywords ({len(orphans)}):\n")
    for kw, doc in orphans:
        print(f"  '{kw}' -> {doc}")


def cmd_duplicates(args):
    """Show duplicate mappings."""
    index = load_json(INDEX_JSON) or {}
    dupes, _ = check_duplicates(index)
    if not dupes:
        print("No duplicate mappings.")
        return
    print(f"Duplicate mappings ({len(dupes)}):\n")
    for kw, doc in dupes:
        print(f"  '{kw}' -> {doc}")


def cmd_refs(args):
    """Show broken cross-references."""
    broken = check_broken_refs()
    if not broken:
        print("No broken references.")
        return
    print(f"Broken references ({len(broken)}):\n")
    for src, target, text in broken:
        print(f"  {src}")
        print(f"    [{text}]({target})")


def cmd_people(args):
    """Show missing people profiles."""
    missing = check_missing_people()
    if not missing:
        print("All mentioned people have profiles.")
        return
    print(f"Missing profiles ({len(missing)}):\n")
    for name, count in missing:
        print(f"  {name} (mentioned {count}x)")
    print(f"\nCreate profiles: docs/people/{{name}}.md")


@mogoj_main
def main():
    parser = argparse.ArgumentParser(
        description="Mogoj Health — memory system health checks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python tools/health.py check\n"
               "  python tools/health.py check --fix\n"
               "  python tools/health.py stale --days 14\n"
               "  python tools/health.py orphans\n"
               "  python tools/health.py people\n",
    )
    add_root_arguments(parser)
    sub = parser.add_subparsers(dest="command")

    p_check = sub.add_parser("check", help="Run all health checks")
    p_check.add_argument("--fix", action="store_true", help="Auto-fix safe issues")

    p_stale = sub.add_parser("stale", help="Show stale documents")
    p_stale.add_argument("--days", type=int, default=30, help="Days threshold (default: 30)")

    sub.add_parser("orphans", help="Show orphan keywords")
    sub.add_parser("duplicates", help="Show duplicate mappings")
    sub.add_parser("refs", help="Show broken cross-references")
    sub.add_parser("people", help="Show missing people profiles")

    args = parser.parse_args()
    report_root(args)
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "check": cmd_check,
        "stale": cmd_stale,
        "orphans": cmd_orphans,
        "duplicates": cmd_duplicates,
        "refs": cmd_refs,
        "people": cmd_people,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
