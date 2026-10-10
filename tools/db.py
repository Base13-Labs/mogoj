#!/usr/bin/env python3
"""
Mogoj DB — SQLite backend with FTS5 full-text search.

Markdown remains source of truth. SQLite accelerates queries.

Commands:
  init      Create mogoj.db with all tables
  sync      Scan markdown files, upsert into DB (idempotent, skips unchanged)
  migrate   First-time: init + sync + copy all keyword mappings from JSON
  status    Show table row counts, DB size, last sync time
  vacuum    Run VACUUM, report size before/after
"""

import argparse
import json
import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Import shared utilities
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (
    ROOT, DB_PATH, INDEX_JSON, GRAPH_JSON,
    SCAN_DIRS, ALL_SEARCH_DIRS,
    file_hash, extract_title, extract_date,
    collect_md_files, relative_doc_path, load_json,
    mogoj_main, PrereqError, add_root_arguments, report_root,
)

SCHEMA = """
-- Core document table
CREATE TABLE IF NOT EXISTS docs (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,
    title TEXT,
    doc_type TEXT,
    created_date TEXT,
    modified_ts REAL,
    size_bytes INTEGER,
    content_hash TEXT
);

-- Full-text search using FTS5
CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
    path, title, content,
    tokenize='porter unicode61'
);

-- Keyword index (mirrors context-index.json)
CREATE TABLE IF NOT EXISTS keywords (
    id INTEGER PRIMARY KEY,
    keyword TEXT NOT NULL,
    doc_id INTEGER NOT NULL REFERENCES docs(id),
    source TEXT DEFAULT 'auto',
    created_ts REAL DEFAULT (unixepoch('now')),
    UNIQUE(keyword, doc_id)
);
CREATE INDEX IF NOT EXISTS idx_keywords_kw ON keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_keywords_doc ON keywords(doc_id);

-- Graph edges (materialized from keyword co-occurrence)
CREATE TABLE IF NOT EXISTS edges (
    doc1_id INTEGER NOT NULL REFERENCES docs(id),
    doc2_id INTEGER NOT NULL REFERENCES docs(id),
    weight INTEGER DEFAULT 1,
    shared_keywords TEXT,
    PRIMARY KEY(doc1_id, doc2_id)
);

-- Access log (for analytics and decay)
CREATE TABLE IF NOT EXISTS access_log (
    id INTEGER PRIMARY KEY,
    doc_id INTEGER REFERENCES docs(id),
    action TEXT,
    ts REAL DEFAULT (unixepoch('now')),
    context TEXT
);

-- Metadata
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


def get_conn():
    """Get a connection to the database."""
    if not DB_PATH.exists():
        raise PrereqError(f"Database not found: {DB_PATH}\nRun 'python3 tools/db.py init' first.")
    return sqlite3.connect(str(DB_PATH))


def infer_doc_type(filepath, content):
    """Infer document type from path and content."""
    path_str = str(filepath).lower()
    content_lower = content.lower()

    if "/decisions/" in path_str:
        return "decision"
    if "/sessions/" in path_str:
        return "session"
    if "/projects/" in path_str:
        return "project"
    if "/company/" in path_str:
        return "company"
    if "/people/" in path_str:
        return "people"

    # Content-based fallback
    if "decision" in content_lower or "decided" in content_lower:
        return "decision"
    if "## status" in content_lower or "## stack" in content_lower:
        return "project"

    return "general"


def cmd_init(args):
    """Create the database with all tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if DB_PATH.exists() and not args.force:
        print(f"Database already exists: {DB_PATH}")
        print("Use --force to recreate.")
        return

    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(str(DB_PATH))
    conn.executescript(SCHEMA)
    conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('created', ?)",
                 (datetime.now().isoformat(),))
    conn.commit()
    conn.close()
    DB_PATH.chmod(0o600)

    print(f"Database created: {DB_PATH}")
    print(f"Size: {DB_PATH.stat().st_size} bytes")


def cmd_sync(args):
    """Scan markdown files and upsert into database."""
    conn = get_conn()

    # Collect all markdown files
    all_dirs = [ROOT / "docs", ROOT / "data" / "sessions", ROOT / "data" / "ram"]
    files = collect_md_files(all_dirs)

    if not files:
        print("No markdown files found.")
        conn.close()
        return

    updated = 0
    skipped = 0

    for filepath in files:
        rel_path = relative_doc_path(filepath)
        new_hash = file_hash(filepath)
        stat = filepath.stat()

        # Check if file has changed
        existing = conn.execute(
            "SELECT id, content_hash FROM docs WHERE path = ?",
            (rel_path,)
        ).fetchone()

        if existing and existing[1] == new_hash:
            skipped += 1
            continue

        # Read content
        try:
            with open(filepath, "r", errors="replace") as f:
                content = f.read()
        except (OSError, IOError):
            continue

        title = extract_title(content)
        doc_type = infer_doc_type(filepath, content)
        created_date = extract_date(content, filepath.name)
        modified_ts = stat.st_mtime
        size_bytes = stat.st_size

        if existing:
            doc_id = existing[0]
            conn.execute(
                "UPDATE docs SET title=?, doc_type=?, created_date=?, "
                "modified_ts=?, size_bytes=?, content_hash=? WHERE id=?",
                (title, doc_type, created_date, modified_ts, size_bytes, new_hash, doc_id)
            )
            # Update FTS
            conn.execute("DELETE FROM docs_fts WHERE rowid=?", (doc_id,))
        else:
            cursor = conn.execute(
                "INSERT INTO docs (path, title, doc_type, created_date, "
                "modified_ts, size_bytes, content_hash) VALUES (?,?,?,?,?,?,?)",
                (rel_path, title, doc_type, created_date, modified_ts, size_bytes, new_hash)
            )
            doc_id = cursor.lastrowid

        # Insert FTS content
        conn.execute(
            "INSERT INTO docs_fts (rowid, path, title, content) VALUES (?,?,?,?)",
            (doc_id, rel_path, title, content)
        )

        updated += 1

    # Update sync timestamp
    conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('last_sync', ?)",
                 (datetime.now().isoformat(),))
    conn.commit()
    conn.close()

    print(f"Synced: {updated} updated, {skipped} unchanged, {len(files)} total files")


def cmd_migrate(args):
    """First-time migration: init + sync + import keywords + build edges."""
    # Step 1: Init
    args.force = True
    cmd_init(args)

    # Step 2: Sync files
    cmd_sync(args)

    # Step 3: Import keywords from context-index.json
    index = load_json(INDEX_JSON)
    if not index:
        print("Warning: No context-index.json found. Skipping keyword import.")
    else:
        conn = get_conn()
        kw_count = 0

        for keyword, doc_paths in index.items():
            for doc_path in doc_paths:
                doc = conn.execute(
                    "SELECT id FROM docs WHERE path = ?", (doc_path,)
                ).fetchone()
                if doc:
                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO keywords (keyword, doc_id, source) "
                            "VALUES (?, ?, 'index')",
                            (keyword, doc[0])
                        )
                        kw_count += 1
                    except sqlite3.IntegrityError:
                        pass

        conn.commit()
        print(f"Imported {kw_count} keyword mappings from context-index.json")

        # Step 4: Build edges from keyword co-occurrence
        _build_edges(conn)
        conn.close()

    print("Migration complete.")


def _build_edges(conn):
    """Build graph edges from keyword co-occurrence in the keywords table."""
    # Get all keyword -> doc_id mappings
    rows = conn.execute("SELECT keyword, doc_id FROM keywords").fetchall()

    kw_to_docs = {}
    for kw, doc_id in rows:
        if kw not in kw_to_docs:
            kw_to_docs[kw] = set()
        kw_to_docs[kw].add(doc_id)

    # Build edges
    edge_data = {}  # (doc1, doc2) -> [keywords]
    for kw, doc_ids in kw_to_docs.items():
        doc_list = sorted(doc_ids)
        for i in range(len(doc_list)):
            for j in range(i + 1, len(doc_list)):
                pair = (doc_list[i], doc_list[j])
                if pair not in edge_data:
                    edge_data[pair] = []
                edge_data[pair].append(kw)

    # Clear and rebuild
    conn.execute("DELETE FROM edges")
    for (d1, d2), keywords in edge_data.items():
        conn.execute(
            "INSERT INTO edges (doc1_id, doc2_id, weight, shared_keywords) VALUES (?,?,?,?)",
            (d1, d2, len(keywords), json.dumps(sorted(keywords)))
        )
        # Also store reverse direction
        conn.execute(
            "INSERT OR IGNORE INTO edges (doc1_id, doc2_id, weight, shared_keywords) VALUES (?,?,?,?)",
            (d2, d1, len(keywords), json.dumps(sorted(keywords)))
        )

    conn.commit()
    total = len(edge_data)
    print(f"Built {total} graph edges")


def cmd_status(args):
    """Show database status."""
    conn = get_conn()

    tables = {
        "docs": conn.execute("SELECT COUNT(*) FROM docs").fetchone()[0],
        "docs_fts": conn.execute("SELECT COUNT(*) FROM docs_fts").fetchone()[0],
        "keywords": conn.execute("SELECT COUNT(*) FROM keywords").fetchone()[0],
        "edges": conn.execute("SELECT COUNT(*) FROM edges").fetchone()[0],
        "access_log": conn.execute("SELECT COUNT(*) FROM access_log").fetchone()[0],
    }

    # Unique keywords
    unique_kw = conn.execute("SELECT COUNT(DISTINCT keyword) FROM keywords").fetchone()[0]

    # Get metadata
    created = conn.execute("SELECT value FROM meta WHERE key='created'").fetchone()
    last_sync = conn.execute("SELECT value FROM meta WHERE key='last_sync'").fetchone()

    db_size = DB_PATH.stat().st_size

    print(f"Database: {DB_PATH}")
    print(f"Size: {db_size:,} bytes ({db_size / 1024:.1f} KB)")
    print(f"Created: {created[0] if created else 'unknown'}")
    print(f"Last sync: {last_sync[0] if last_sync else 'never'}")
    print()
    print(f"Tables:")
    print(f"  docs:       {tables['docs']:>6d} rows")
    print(f"  docs_fts:   {tables['docs_fts']:>6d} rows")
    print(f"  keywords:   {tables['keywords']:>6d} rows ({unique_kw} unique)")
    print(f"  edges:      {tables['edges']:>6d} rows ({tables['edges'] // 2} undirected)")
    print(f"  access_log: {tables['access_log']:>6d} rows")

    # Doc type breakdown
    types = conn.execute(
        "SELECT doc_type, COUNT(*) FROM docs GROUP BY doc_type ORDER BY COUNT(*) DESC"
    ).fetchall()
    if types:
        print(f"\nDoc types:")
        for dtype, count in types:
            print(f"  {dtype or 'unknown':<12s} {count:>4d}")

    conn.close()


def cmd_vacuum(args):
    """Run VACUUM to reclaim space."""
    before = DB_PATH.stat().st_size
    conn = get_conn()
    conn.execute("VACUUM")
    conn.close()
    after = DB_PATH.stat().st_size
    saved = before - after
    print(f"Before: {before:,} bytes")
    print(f"After:  {after:,} bytes")
    print(f"Saved:  {saved:,} bytes ({saved / max(before, 1) * 100:.1f}%)")


@mogoj_main
def main():
    parser = argparse.ArgumentParser(
        description="Mogoj DB — SQLite backend with FTS5 search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Examples:\n"
               "  python tools/db.py init\n"
               "  python tools/db.py migrate      # first-time: init + sync + import\n"
               "  python tools/db.py sync          # update after new sessions\n"
               "  python tools/db.py status\n"
               "  python tools/db.py vacuum\n",
    )
    add_root_arguments(parser)
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="Create database with all tables")
    p_init.add_argument("--force", "-f", action="store_true", help="Recreate if exists")

    sub.add_parser("sync", help="Scan markdown and upsert into DB")
    sub.add_parser("migrate", help="First-time: init + sync + import keywords + build edges")
    sub.add_parser("status", help="Show database status")
    sub.add_parser("vacuum", help="Run VACUUM to reclaim space")

    args = parser.parse_args()
    report_root(args)
    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "init": cmd_init,
        "sync": cmd_sync,
        "migrate": cmd_migrate,
        "status": cmd_status,
        "vacuum": cmd_vacuum,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
