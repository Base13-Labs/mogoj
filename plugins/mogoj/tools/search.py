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
import re
import sys
from pathlib import Path

# Import shared utilities
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    ROOT, TYPE_DIRS, ALL_SEARCH_DIRS, DB_PATH,
    collect_md_files, relative_path, mogoj_main, add_root_arguments, report_root,
)


def search_file(filepath, pattern, context_lines=1):
    """Search a file for pattern matches. Returns list of match dicts."""
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


# ---------------------------------------------------------------------------
# FTS5 search (Phase 2 — used when mogoj.db exists)
# ---------------------------------------------------------------------------

def fts5_search(query, type_filter=None, after=None, before=None,
                limit=20, show_score=False):
    """Search using SQLite FTS5. Returns True if results found, False if DB missing."""
    if not DB_PATH.exists():
        return None  # signal: DB not available, fall back to regex

    import sqlite3
    conn = sqlite3.connect(str(DB_PATH))
    try:
        # Build FTS5 query
        parts = ["SELECT d.path, d.title, d.doc_type, d.created_date,"]
        parts.append("  rank AS score")
        parts.append("FROM docs_fts fts")
        parts.append("JOIN docs d ON d.id = fts.rowid")
        parts.append("WHERE docs_fts MATCH ?")

        params = [query]
        conditions = []

        if type_filter:
            conditions.append("d.doc_type = ?")
            params.append(type_filter)
        if after:
            conditions.append("d.created_date >= ?")
            params.append(after)
        if before:
            conditions.append("d.created_date <= ?")
            params.append(before)

        for cond in conditions:
            parts.append(f"  AND {cond}")

        parts.append("ORDER BY rank")
        parts.append(f"LIMIT {limit}")

        sql = "\n".join(parts)
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()

        if not rows:
            print(f"No FTS5 matches for '{query}'.")
            # Try to find graph-related docs
            _show_related(conn, query)
            return True

        print(f"Found {len(rows)} result(s) via FTS5:\n")
        for path, title, doc_type, created_date, score in rows:
            title_str = title or "(untitled)"
            date_str = f"  [{created_date}]" if created_date else ""
            score_str = f"  (score: {score:.2f})" if show_score else ""
            print(f"  {path}")
            print(f"    {title_str}  [{doc_type}]{date_str}{score_str}")
            print()

        # Show related docs from graph
        _show_related_for_paths(conn, [r[0] for r in rows[:3]])
        return True
    except sqlite3.OperationalError:
        return None  # table doesn't exist, fall back
    finally:
        conn.close()


def _show_related(conn, query):
    """Show graph-related docs for a query by finding keyword matches."""
    try:
        cursor = conn.execute(
            "SELECT DISTINCT d.path, COUNT(*) as cnt "
            "FROM keywords k JOIN docs d ON d.id = k.doc_id "
            "WHERE k.keyword LIKE ? "
            "GROUP BY d.path ORDER BY cnt DESC LIMIT 5",
            (f"%{query.split()[0].lower()}%",)
        )
        related = cursor.fetchall()
        if related:
            print("Related docs (via keywords):")
            for path, cnt in related:
                print(f"  [{cnt} keywords] {path}")
            print()
    except sqlite3.OperationalError:
        pass


def _show_related_for_paths(conn, paths):
    """Show graph-related docs for given doc paths."""
    if not paths:
        return
    try:
        placeholders = ",".join("?" * len(paths))
        cursor = conn.execute(
            f"SELECT e.doc2_id, d2.path, e.weight, e.shared_keywords "
            f"FROM edges e "
            f"JOIN docs d1 ON d1.id = e.doc1_id "
            f"JOIN docs d2 ON d2.id = e.doc2_id "
            f"WHERE d1.path IN ({placeholders}) "
            f"AND d2.path NOT IN ({placeholders}) "
            f"ORDER BY e.weight DESC LIMIT 5",
            paths + paths
        )
        related = cursor.fetchall()
        if related:
            print("Related docs (via graph):")
            for _, path, weight, shared_kw in related:
                print(f"  [{weight} shared] {path}")
            print()
    except sqlite3.OperationalError:
        pass


# ---------------------------------------------------------------------------
# Regex search (original, used as fallback)
# ---------------------------------------------------------------------------

def regex_search(query, args):
    """Original regex-based search."""
    flags = 0 if args.case_sensitive else re.IGNORECASE
    try:
        if args.regex:
            pattern = re.compile(query, flags)
        else:
            pattern = re.compile(re.escape(query), flags)
    except re.error as e:
        print(f"Invalid regex: {e}", file=sys.stderr)
        sys.exit(1)

    if args.type:
        dirs = TYPE_DIRS[args.type]
    else:
        dirs = ALL_SEARCH_DIRS
    files = collect_md_files(dirs)

    if not files:
        print("No markdown files found to search.")
        return

    results = []
    for f in files:
        matches = search_file(f, pattern, args.context)
        if matches:
            results.append((f, matches))

    if not results:
        print(f"No matches for '{query}'.")
        return

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


@mogoj_main
def main():
    parser = argparse.ArgumentParser(
        description="Full-text search across brain markdown files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python tools/search.py chatx\n"
               "  python tools/search.py 'sales sprint' --type sessions\n"
               '  python tools/search.py "dental|whatsapp" --regex\n'
               "  python tools/search.py idea --type projects --context 3\n"
               "  python tools/search.py 'pricing' --after 2026-04-01\n"
               "  python tools/search.py 'sprint' --last-week\n",
    )
    add_root_arguments(parser)
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

    # FTS5 / temporal search options
    parser.add_argument("--after", help="Only docs created/modified after this date (YYYY-MM-DD)")
    parser.add_argument("--before", help="Only docs created/modified before this date (YYYY-MM-DD)")
    parser.add_argument("--last-week", action="store_true",
                        help="Only docs from the last 7 days")
    parser.add_argument("--last-month", action="store_true",
                        help="Only docs from the last 30 days")
    parser.add_argument("--limit", type=int, default=20,
                        help="Max results for FTS5 search (default: 20)")
    parser.add_argument("--score", action="store_true",
                        help="Show BM25 relevance score (FTS5 only)")

    args = parser.parse_args()
    report_root(args)

    # Handle temporal shortcuts
    if args.last_week or args.last_month:
        from datetime import date, timedelta
        today = date.today()
        if args.last_week:
            args.after = (today - timedelta(days=7)).isoformat()
        elif args.last_month:
            args.after = (today - timedelta(days=30)).isoformat()

    # Try FTS5 search first if temporal filters are used or DB exists
    use_fts = args.after or args.before or args.score
    if use_fts or DB_PATH.exists():
        result = fts5_search(
            args.query,
            type_filter=args.type,
            after=args.after,
            before=args.before,
            limit=args.limit,
            show_score=args.score,
        )
        if result is not None:
            return  # FTS5 handled it
        if use_fts:
            print("(SQLite DB not found — temporal/score filters need: python3 tools/db.py init && python3 tools/db.py sync)",
                  file=sys.stderr)
            print("Falling back to regex search...\n", file=sys.stderr)

    # Fallback: original regex search
    regex_search(args.query, args)


if __name__ == "__main__":
    main()
