#!/usr/bin/env python3
"""Safe store migration, backup, rebuild, and rollback operations."""

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    ROOT, DB_PATH, INDEX_JSON, INDEX_MD, GRAPH_JSON, STORE_MARKER,
    add_root_arguments, report_root, load_json, mogoj_main, MogojError,
    EXIT_CORRUPT,
)


BACKUP_DIR = ROOT / ".mogoj" / "backups"
STATE_PATH = ROOT / ".mogoj" / "migration-state.json"
GENERATED_FILES = (DB_PATH, INDEX_JSON, INDEX_MD, GRAPH_JSON)
EXCLUDED_PARTS = {".git", "__pycache__"}


def _timestamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


def _write_json_atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def _iter_backup_files():
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        if relative.parts[:2] == (".mogoj", "backups"):
            continue
        if path.name.endswith((".migrating", ".tmp")):
            continue
        yield path, relative


def backup_store(label="backup", dry_run=False):
    """Create a timestamped, private ZIP snapshot of the store."""
    destination = BACKUP_DIR / f"{_timestamp()}-{label}.zip"
    files = list(_iter_backup_files())
    if dry_run:
        print(f"Would back up {len(files)} files to {destination}")
        return destination

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "format": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "root": str(ROOT),
        "files": [],
    }
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, relative in files:
            data = path.read_bytes()
            archive.writestr(str(relative), data)
            manifest["files"].append({
                "path": str(relative),
                "sha256": hashlib.sha256(data).hexdigest(),
                "size": len(data),
            })
        archive.writestr(".mogoj/backup-manifest.json", json.dumps(manifest, indent=2) + "\n")
    destination.chmod(0o600)
    print(f"Backup created: {destination}")
    return destination


def _document_path(doc_path):
    for candidate in (ROOT / "docs" / doc_path, ROOT / "data" / doc_path, ROOT / doc_path):
        if candidate.is_file():
            return candidate
    return None


def audit_store():
    """Report duplicate Markdown content and stale keyword mappings."""
    hashes = {}
    for directory in (ROOT / "docs", ROOT / "data" / "sessions", ROOT / "data" / "ram"):
        if not directory.exists():
            continue
        for path in directory.rglob("*.md"):
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            hashes.setdefault(digest, []).append(path.relative_to(ROOT))
    duplicates = [paths for paths in hashes.values() if len(paths) > 1]

    stale = []
    index = load_json(INDEX_JSON) or {}
    for keyword, paths in index.items():
        for path in paths:
            if _document_path(path) is None:
                stale.append((keyword, path))

    print(f"Duplicate document groups: {len(duplicates)}")
    for paths in duplicates:
        print("  - " + ", ".join(map(str, paths)))
    print(f"Stale JSON mappings: {len(stale)}")
    for keyword, path in stale:
        print(f"  - {keyword}: {path}")
    return duplicates, stale


def _recover_interrupted_stage():
    stage = DB_PATH.with_suffix(DB_PATH.suffix + ".migrating")
    if stage.exists():
        stage.unlink()
        print(f"Recovered interrupted migration: removed {stage.name}")


def rebuild_database(dry_run=False, label="rebuild"):
    """Build SQLite in a staging file and atomically publish it."""
    stage = DB_PATH.with_suffix(DB_PATH.suffix + ".migrating")
    if dry_run:
        print(f"Would build database at {stage} and atomically replace {DB_PATH}")
        audit_store()
        return None

    _recover_interrupted_stage()
    backup = backup_store(label)
    _write_json_atomic(STATE_PATH, {
        "status": "in_progress", "operation": label,
        "backup": str(backup), "started_at": datetime.now(timezone.utc).isoformat(),
    })
    env = os.environ.copy()
    env["MOGOJ_ROOT"] = str(ROOT)
    env["MOGOJ_DB_PATH"] = str(stage)
    command = [sys.executable, str(Path(__file__).with_name("db.py")), "migrate"]
    try:
        subprocess.run(command, env=env, check=True)
        with sqlite3.connect(str(stage)) as connection:
            result = connection.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise MogojError("Staged database failed integrity_check", EXIT_CORRUPT)
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        os.replace(stage, DB_PATH)
        marker = ROOT / STORE_MARKER
        _write_json_atomic(marker, {
            "format": 1,
            "migrated_at": datetime.now(timezone.utc).isoformat(),
        })
        _write_json_atomic(STATE_PATH, {
            "status": "complete", "operation": label,
            "backup": str(backup), "completed_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception:
        if stage.exists():
            stage.unlink()
        raise
    audit_store()
    print(f"{label.capitalize()} complete. Markdown source files were not deleted.")
    return backup


def rollback(backup_name=None, dry_run=False):
    """Restore generated artifacts from a backup; leave Markdown untouched."""
    if backup_name:
        backup = Path(backup_name).expanduser().resolve()
    else:
        backups = sorted(BACKUP_DIR.glob("*.zip"), reverse=True)
        if not backups:
            raise MogojError("No Mogoj backups found")
        backup = backups[0]
    if not backup.is_file() or BACKUP_DIR.resolve() not in backup.parents:
        raise MogojError(f"Invalid backup: {backup}")

    generated = {str(path.relative_to(ROOT)): path for path in GENERATED_FILES}
    if dry_run:
        print(f"Would restore generated artifacts from {backup}")
        return
    with zipfile.ZipFile(backup) as archive:
        names = set(archive.namelist())
        for relative, destination in generated.items():
            if relative not in names:
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(destination.suffix + ".rollback")
            temporary.write_bytes(archive.read(relative))
            os.replace(temporary, destination)
            print(f"Restored: {relative}")
    print("Rollback complete. Markdown files were left unchanged.")


@mogoj_main
def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description="Mogoj safe store migration utilities")
    add_root_arguments(parser)
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate", help="Back up and migrate an existing store")
    sub.add_parser("backup", help="Create a timestamped store backup")
    sub.add_parser("rebuild", help="Safely rebuild generated SQLite state")
    rollback_parser = sub.add_parser("rollback", help="Restore generated state from a backup")
    rollback_parser.add_argument("--backup", help="Backup ZIP (defaults to newest)")
    args = parser.parse_args()
    report_root(args)
    if args.command == "backup":
        backup_store(dry_run=args.dry_run)
    elif args.command in ("migrate", "rebuild"):
        rebuild_database(dry_run=args.dry_run, label=args.command)
    else:
        rollback(args.backup, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
