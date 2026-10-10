#!/usr/bin/env python3
"""Beginner-friendly command surface for Mogoj."""

import argparse
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from security import detect_secrets, redact_secrets  # noqa: E402


ENGINE = Path(__file__).resolve().parents[1]
VERSION = (ENGINE / "VERSION").read_text().strip()
MARKER = Path(".mogoj/store.json")

if sys.version_info < (3, 9):
    print(
        "Mogoj requires Python 3.9 or newer. Install a supported Python and retry.",
        file=sys.stderr,
    )
    sys.exit(4)


class CliError(Exception):
    pass


def emit(value, as_json=False):
    if as_json:
        print(json.dumps(value, indent=2, default=str))
    elif isinstance(value, str):
        print(value)


def initialized(path):
    return (path / MARKER).is_file()


def resolve_root(args, allow_missing=False):
    configured = getattr(args, "root", None) or os.environ.get("MOGOJ_ROOT")
    if configured:
        root = Path(configured).expanduser().resolve()
        if not allow_missing and not root.is_dir():
            raise CliError(f"Memory store not found at {root}. Run: mogoj init {root}")
        return root
    cwd = Path.cwd().resolve()
    for candidate in (cwd, *cwd.parents):
        if initialized(candidate):
            return candidate
    default = (Path.home() / ".mogoj").resolve()
    if allow_missing or initialized(default):
        return default
    raise CliError("No Mogoj store found. Start with: mogoj init")


def run_tool(root, tool, arguments, capture=False):
    command = [sys.executable, str(ENGINE / "tools" / tool), "--root", str(root), *arguments]
    completed = subprocess.run(
        command, text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )
    if completed.returncode:
        message = (completed.stderr or completed.stdout or f"{tool} failed").strip()
        raise CliError(message)
    return completed.stdout if capture else ""


def cmd_init(args):
    if args.path and args.root:
        raise CliError("Use either 'mogoj init PATH' or '--root PATH', not both.")
    if args.path:
        args.root = args.path
    root = resolve_root(args, allow_missing=True)
    nonempty = root.exists() and any(root.iterdir())
    if nonempty and not initialized(root) and not args.yes:
        if not sys.stdin.isatty():
            raise CliError(f"{root} is not empty. Re-run with --yes after checking the path.")
        answer = input(f"Use the existing non-empty folder {root}? [y/N] ").strip().lower()
        if answer not in ("y", "yes"):
            raise CliError("Initialization cancelled; nothing was changed.")

    directories = (
        ".mogoj/backups", "docs/notes", "docs/projects", "docs/decisions",
        "docs/company", "docs/people", "data/sessions", "data/index",
        "data/db", "data/ram/archive", "imports",
    )
    for directory in directories:
        (root / directory).mkdir(parents=True, exist_ok=True)
        (root / directory).chmod(0o700)
    marker = root / MARKER
    if not marker.exists():
        marker.write_text(json.dumps({
            "format": 1,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "mogoj_version": VERSION,
        }, indent=2) + "\n")
        marker.chmod(0o600)
    config = root / "config.ini"
    if not config.exists():
        shutil.copy2(ENGINE / "config.ini.example", config)
        config.chmod(0o600)
    current = root / "data" / "ram" / "current.md"
    if not current.exists():
        current.write_text("# Active memory\n\nNo active session yet.\n")
        current.chmod(0o600)
    privacy_ignore = root / ".gitignore"
    if not privacy_ignore.exists():
        privacy_ignore.write_text(
            ".env\n.env.*\n.mogoj/backups/\ndata/db/\nimports/\n*.log\n"
        )
    result = {"ok": True, "root": str(root), "version": VERSION}
    if args.json:
        emit(result, True)
    else:
        print(f"Mogoj is ready at {root}")
        print("Next: mogoj save \"My first memory\" --title \"First memory\"")


def cmd_onboard(args):
    """Guide store location, agent choice, and optional Markdown import."""
    if args.memory_path:
        memory_path = args.memory_path
    elif args.root:
        memory_path = args.root
    elif sys.stdin.isatty():
        default = str(Path.home() / ".mogoj")
        memory_path = input(f"Where should private memory live? [{default}] ").strip() or default
    else:
        memory_path = str(Path.home() / ".mogoj")
    agents = args.agents
    if agents is None and sys.stdin.isatty():
        agents = input("Connect agents (codex, claude, both, or none)? [both] ").strip() or "both"
    agents = agents or "none"
    init_args = argparse.Namespace(path=memory_path, root=None, yes=args.yes, json=False)
    cmd_init(init_args)
    root = Path(memory_path).expanduser().resolve()
    integration = root / ".mogoj" / "integrations.json"
    integration.write_text(json.dumps({"agents": agents}, indent=2) + "\n")
    integration.chmod(0o600)
    import_path = args.import_path
    if import_path is None and sys.stdin.isatty():
        import_path = input("Folder of existing Markdown to import (Enter to skip): ").strip() or None
    imported = 0
    if import_path:
        source = Path(import_path).expanduser().resolve()
        if not source.is_dir():
            raise CliError(f"Import folder not found: {source}")
        for markdown in sorted(source.rglob("*.md")):
            run_tool(root, "ingest.py", ["import", str(markdown)], capture=True)
            imported += 1
    result = {"ok": True, "root": str(root), "agents": agents, "imported": imported}
    if args.json:
        emit(result, True)
    else:
        print(f"Onboarding complete. Agent choice: {agents}; imported: {imported}.")
        print("Try: mogoj save \"My first memory\" --title \"First memory\"")
        print("Then: mogoj rebuild && mogoj search \"first memory\"")


def markdown_files(root):
    files = []
    for directory in (root / "docs", root / "data" / "sessions", root / "data" / "ram"):
        if directory.exists():
            files.extend(path for path in directory.rglob("*.md") if path.is_file())
    return sorted(set(files))


def cmd_status(args):
    root = resolve_root(args)
    files = markdown_files(root)
    database = root / "data" / "db" / "mogoj.db"
    result = {
        "ok": initialized(root), "root": str(root), "version": VERSION,
        "markdown_documents": len(files), "database_ready": database.is_file(),
        "last_modified": max((path.stat().st_mtime for path in files), default=None),
    }
    if args.json:
        emit(result, True)
    else:
        print(f"Mogoj store: {root}")
        print(f"Markdown memories: {len(files)}")
        print(f"Search database: {'ready' if database.is_file() else 'not built (run: mogoj rebuild)'}")


def _slug(value):
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:60] or "memory"


def cmd_save(args):
    root = resolve_root(args)
    text = args.text
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    if not text:
        raise CliError("Add memory text, for example: mogoj save \"Customer prefers email\"")
    findings = detect_secrets(text)
    if findings and args.redact:
        text = redact_secrets(text)
    elif findings and not args.allow_secrets:
        labels = ", ".join(findings)
        raise CliError(
            f"Possible secret detected ({labels}). The value was not printed or saved. "
            "Use --redact, or --allow-secrets only if this private store is appropriate."
        )
    title = args.title or text.splitlines()[0][:80]
    kind_dir = {
        "note": "notes", "project": "projects", "decision": "decisions",
        "company": "company", "person": "people",
    }[args.type]
    day = datetime.now(timezone.utc).date().isoformat()
    destination = root / "docs" / kind_dir / f"{day}-{_slug(title)}.md"
    try:
        destination.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise CliError("Refusing to write through a path outside the memory store.") from exc
    if destination.is_symlink():
        raise CliError("Refusing to overwrite a symbolic link.")
    if destination.exists() and not args.force:
        raise CliError(f"Memory already exists: {destination}. Use --force to replace it.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        f"# {title}\n\nDate: {day}\nType: {args.type}\n\n{text.strip()}\n"
    )
    destination.chmod(0o600)
    database = root / "data" / "db" / "mogoj.db"
    if database.is_file():
        run_tool(root, "db.py", ["sync"], capture=True)
    result = {"ok": True, "path": str(destination.relative_to(root)), "root": str(root)}
    emit(result if args.json else f"Saved: {result['path']}", args.json)


def cmd_search(args):
    root = resolve_root(args)
    arguments = [args.query, "--budget-tokens", str(args.budget_tokens), "--json"]
    if args.type:
        arguments.extend(["--type", args.type])
    if args.project:
        arguments.extend(["--project", args.project])
    output = run_tool(root, "retrieve.py", arguments, capture=True)
    result = json.loads(output)
    emit(result if args.json else result["context"], args.json)


def cmd_recent(args):
    root = resolve_root(args)
    files = sorted(markdown_files(root), key=lambda path: path.stat().st_mtime, reverse=True)
    results = [{
        "path": str(path.relative_to(root)),
        "modified_at": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
    } for path in files[:args.limit]]
    if args.json:
        emit({"root": str(root), "results": results}, True)
    elif not results:
        print("No memories yet. Add one with: mogoj save \"Your note\"")
    else:
        for item in results:
            print(f"{item['modified_at']}  {item['path']}")


def cmd_doctor(args):
    root = resolve_root(args)
    checks = []

    def check(name, ok, detail, severity="error"):
        checks.append({"name": name, "status": "ok" if ok else severity, "detail": detail})

    check("Python", sys.version_info >= (3, 9), sys.version.split()[0])
    try:
        with sqlite3.connect(":memory:") as connection:
            connection.execute("CREATE VIRTUAL TABLE test_fts USING fts5(content)")
        fts_ok, fts_detail = True, "SQLite FTS5 available"
    except sqlite3.Error as exc:
        fts_ok, fts_detail = False, str(exc)
    check("SQLite FTS5", fts_ok, fts_detail)
    check("Store marker", initialized(root), str(root / MARKER))
    check("Store writable", os.access(root, os.W_OK), str(root))
    check(
        "Git privacy", not (root / ".git").exists(),
        "store is not a Git repository" if not (root / ".git").exists()
        else "store is a Git repository; confirm its remote is private before committing memories",
        "warning",
    )
    check("Configuration", (root / "config.ini").is_file(), str(root / "config.ini"), "warning")

    files = markdown_files(root)
    database = root / "data" / "db" / "mogoj.db"
    db_docs = None
    integrity = None
    if database.is_file():
        try:
            with sqlite3.connect(str(database)) as connection:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
                db_docs = connection.execute("SELECT count(*) FROM docs").fetchone()[0]
        except sqlite3.Error as exc:
            integrity = str(exc)
    check("Database integrity", integrity == "ok", integrity or "not built; run: mogoj rebuild", "warning")
    check(
        "Index drift", db_docs == len(files) if db_docs is not None else False,
        f"SQLite: {db_docs if db_docs is not None else 'not built'}; Markdown: {len(files)}",
        "warning",
    )
    home = Path.home()
    claude_ready = (home / ".claude").exists()
    codex_ready = (home / ".codex").exists()
    check("Claude integration", claude_ready, "Claude directory detected" if claude_ready else "not installed", "warning")
    check("Codex integration", codex_ready, "Codex directory detected" if codex_ready else "not installed", "warning")
    result = {
        "ok": not any(item["status"] == "error" for item in checks),
        "root": str(root), "version": VERSION, "checks": checks,
    }
    if args.json:
        emit(result, True)
    else:
        for item in checks:
            symbol = {"ok": "✓", "warning": "!", "error": "✗"}[item["status"]]
            print(f"{symbol} {item['name']}: {item['detail']}")
        print("Doctor found no blocking problems." if result["ok"] else "Doctor found a blocking problem.")
    return 0 if result["ok"] else 1


def cmd_maintenance(args):
    root = resolve_root(args)
    arguments = []
    if args.dry_run:
        arguments.append("--dry-run")
    arguments.append(args.command)
    if args.command == "rollback" and args.backup:
        arguments.extend(["--backup", args.backup])
    output = run_tool(root, "migrate.py", arguments, capture=True)
    if args.json:
        emit({"ok": True, "root": str(root), "command": args.command, "output": output.strip()}, True)
    elif output:
        print(output, end="" if output.endswith("\n") else "\n")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="mogoj",
        description="Local, portable memory for AI coding assistants",
        epilog=(
            "Examples:\n"
            "  mogoj init\n"
            "  mogoj save \"We chose SQLite for local search\" --type decision\n"
            "  mogoj rebuild\n"
            "  mogoj search \"Why SQLite?\"\n"
            "  mogoj doctor"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--root", help="Memory store path (overrides MOGOJ_ROOT)")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    sub = parser.add_subparsers(dest="command", required=True)

    init_parser = sub.add_parser("init", help="Create a memory store")
    init_parser.add_argument("path", nargs="?")
    init_parser.add_argument("--yes", action="store_true", help="Accept an existing non-empty folder")
    init_parser.set_defaults(func=cmd_init)

    onboard_parser = sub.add_parser("onboard", help="Guided first-run setup")
    onboard_parser.add_argument("--memory-path")
    onboard_parser.add_argument("--agents", choices=("codex", "claude", "both", "none"))
    onboard_parser.add_argument("--import-path")
    onboard_parser.add_argument("--yes", action="store_true")
    onboard_parser.set_defaults(func=cmd_onboard)

    sub.add_parser("status", help="Show store status").set_defaults(func=cmd_status)
    sub.add_parser("doctor", help="Diagnose setup and integrations").set_defaults(func=cmd_doctor)

    save_parser = sub.add_parser("save", help="Save a Markdown memory")
    save_parser.add_argument("text", nargs="?")
    save_parser.add_argument("--title")
    save_parser.add_argument("--type", choices=("note", "project", "decision", "company", "person"), default="note")
    save_parser.add_argument("--force", action="store_true")
    save_parser.add_argument("--redact", action="store_true", help="Replace detected secrets before saving")
    save_parser.add_argument("--allow-secrets", action="store_true", help="Save despite a secret warning")
    save_parser.set_defaults(func=cmd_save)

    search_parser = sub.add_parser("search", help="Retrieve bounded, cited context")
    search_parser.add_argument("query")
    search_parser.add_argument("--budget-tokens", type=int, default=1200)
    search_parser.add_argument("--type")
    search_parser.add_argument("--project")
    search_parser.set_defaults(func=cmd_search)

    recent_parser = sub.add_parser("recent", help="List recently changed memories")
    recent_parser.add_argument("--limit", type=int, default=10)
    recent_parser.set_defaults(func=cmd_recent)

    for command in ("migrate", "backup", "rebuild", "rollback"):
        maintenance = sub.add_parser(command, help=f"Safely {command} store state")
        maintenance.add_argument("--dry-run", action="store_true")
        if command == "rollback":
            maintenance.add_argument("--backup")
        maintenance.set_defaults(func=cmd_maintenance)

    version_parser = sub.add_parser("version", help="Print the installed version")
    version_parser.set_defaults(func=lambda args: emit({"version": VERSION} if args.json else VERSION, args.json))
    return parser


def main():
    os.umask(0o077)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    parser = build_parser()
    args = parser.parse_args()
    try:
        result = args.func(args)
        return result if isinstance(result, int) else 0
    except (CliError, ValueError, OSError) as exc:
        if args.json:
            emit({"ok": False, "error": str(exc)}, True)
        else:
            print(f"Mogoj could not continue: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
