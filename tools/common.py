#!/usr/bin/env python3
"""
Mogoj Common — shared utilities for all brain tools.

Provides: repo root detection, path constants, stop words, keyword extraction,
file collection, JSON I/O, hashing, metadata extraction, and error handling.
"""

import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

EXIT_OK = 0
EXIT_NOT_FOUND = 1
EXIT_BAD_INPUT = 2
EXIT_CORRUPT = 3
EXIT_PREREQ = 4  # missing prerequisite (e.g., index not built)


class MogojError(Exception):
    """Base exception for Mogoj tools."""
    def __init__(self, message, exit_code=1):
        super().__init__(message)
        self.exit_code = exit_code


class NotFoundError(MogojError):
    def __init__(self, message):
        super().__init__(message, EXIT_NOT_FOUND)


class BadInputError(MogojError):
    def __init__(self, message):
        super().__init__(message, EXIT_BAD_INPUT)


class CorruptDataError(MogojError):
    def __init__(self, message):
        super().__init__(message, EXIT_CORRUPT)


class PrereqError(MogojError):
    def __init__(self, message):
        super().__init__(message, EXIT_PREREQ)


def mogoj_main(main_func):
    """Wrapper for tool main() that catches MogojError and exits cleanly."""
    def wrapper(*args, **kwargs):
        try:
            return main_func(*args, **kwargs)
        except MogojError as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(e.exit_code)
    return wrapper


# ---------------------------------------------------------------------------
# Repo root detection (single canonical implementation)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

ROOT = find_repo_root()

INDEX_JSON = ROOT / "data" / "index" / "context-index.json"
INDEX_MD = ROOT / "data" / "index" / "context-index.md"
GRAPH_JSON = ROOT / "data" / "index" / "graph.json"
DB_PATH = ROOT / "data" / "db" / "mogoj.db"

RAM_DIR = ROOT / "data" / "ram"
CURRENT_RAM = RAM_DIR / "current.md"
ARCHIVE_DIR = RAM_DIR / "archive"

SCAN_DIRS = [ROOT / "docs", ROOT / "data" / "sessions"]

# Type filters for search (maps type name -> list of directories)
TYPE_DIRS = {
    "sessions": [ROOT / "data" / "sessions", ROOT / "docs" / "sessions"],
    "projects": [ROOT / "docs" / "projects"],
    "decisions": [ROOT / "docs" / "decisions"],
    "company":  [ROOT / "docs" / "company"],
    "people":   [ROOT / "docs" / "people"],
    "ram":      [ROOT / "data" / "ram"],
    "imports":  [ROOT / "imports"],
}

ALL_SEARCH_DIRS = [ROOT / "docs", ROOT / "data", ROOT / "imports"]


# ---------------------------------------------------------------------------
# Stop words (unified, expanded from index.py + ingest.py)
# ---------------------------------------------------------------------------

STOP_WORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "but", "by",
    "can", "could", "did", "do", "does", "for", "from", "had", "has", "have",
    "how", "if", "in", "into", "is", "it", "its", "may", "more", "most",
    "not", "of", "on", "or", "out", "over", "own", "per", "should", "so",
    "some", "than", "that", "the", "their", "them", "then", "there", "these",
    "they", "this", "through", "to", "too", "upon", "use", "used", "using",
    "very", "was", "were", "what", "when", "which", "while", "who", "will",
    "with", "would",
})

# Headings that are too generic to index as keywords
GENERIC_HEADINGS = frozenset({
    "summary", "overview", "notes", "context", "details", "background",
    "references", "links", "appendix", "introduction", "conclusion",
    "table of contents", "toc",
})

# Import configurable values (config.ini overrides these defaults)
try:
    from config import (
        MIN_KEYWORD_LENGTH as _CFG_MIN_KW,
        MAX_KEYWORDS_PER_DOC as _CFG_MAX_KW,
        HASH_LENGTH as _CFG_HASH,
        FINGERPRINT_LENGTH as _CFG_FP,
    )
    MIN_KEYWORD_LENGTH = _CFG_MIN_KW
    MAX_KEYWORDS_PER_DOC = _CFG_MAX_KW
except ImportError:
    MIN_KEYWORD_LENGTH = 3
    MAX_KEYWORDS_PER_DOC = 20


# ---------------------------------------------------------------------------
# Keyword extraction (merged best of index.py + ingest.py)
# ---------------------------------------------------------------------------

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
        if heading.lower() in GENERIC_HEADINGS:
            continue
        words = re.findall(r"[a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)*", heading.lower())
        for w in words:
            if len(w) >= MIN_KEYWORD_LENGTH and w not in STOP_WORDS:
                keywords.add(w)

    # Extract bold terms (**term**)
    for match in re.finditer(r"\*\*([^*]+)\*\*", content):
        term = match.group(1).strip().lower()
        slug = re.sub(r"[^a-z0-9]+", "-", term).strip("-")
        if slug and len(slug) >= MIN_KEYWORD_LENGTH:
            keywords.add(slug)
        words = re.findall(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", term)
        for w in words:
            if len(w) >= MIN_KEYWORD_LENGTH and w not in STOP_WORDS:
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
                    if len(v) >= MIN_KEYWORD_LENGTH:
                        keywords.add(v)

    return keywords


# ---------------------------------------------------------------------------
# File collection
# ---------------------------------------------------------------------------

def collect_md_files(dirs=None):
    """Collect all .md files from given directories (default: SCAN_DIRS)."""
    if dirs is None:
        dirs = SCAN_DIRS
    files = []
    for d in dirs:
        if not d.exists():
            continue
        for f in d.rglob("*.md"):
            files.append(f)
    return files


# ---------------------------------------------------------------------------
# JSON I/O
# ---------------------------------------------------------------------------

def load_json(path):
    """Load a JSON file, return parsed data. Returns None if not found."""
    p = Path(path)
    if not p.exists():
        return None
    try:
        with open(p, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise CorruptDataError(f"Failed to load {p}: {e}")


def save_json(path, data, sort_keys=True):
    """Save data to a JSON file with optional key sorting."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, sort_keys=sort_keys)


# ---------------------------------------------------------------------------
# Hashing and fingerprinting
# ---------------------------------------------------------------------------

try:
    HASH_LENGTH = _CFG_HASH
    FINGERPRINT_LENGTH = _CFG_FP
except NameError:
    HASH_LENGTH = 8       # file hash: 8 hex chars (32 bits)
    FINGERPRINT_LENGTH = 12  # directory fingerprint: 12 hex chars (48 bits)
CHUNK_SIZE = 8192


def file_hash(filepath):
    """Compute SHA-256 prefix of file content."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
            h.update(chunk)
    return h.hexdigest()[:HASH_LENGTH]


def dir_fingerprint(dirpath):
    """Compute SHA-256 fingerprint of all files in directory."""
    h = hashlib.sha256()
    dp = Path(dirpath)
    file_count = 0
    total_size = 0
    for fp in sorted(dp.rglob("*")):
        if fp.is_file():
            file_count += 1
            total_size += fp.stat().st_size
            h.update(str(fp.relative_to(dp)).encode())
            with open(fp, "rb") as f:
                for chunk in iter(lambda: f.read(CHUNK_SIZE), b""):
                    h.update(chunk)
    return h.hexdigest()[:FINGERPRINT_LENGTH], file_count, total_size


# ---------------------------------------------------------------------------
# Metadata extraction
# ---------------------------------------------------------------------------

def extract_title(content):
    """Extract first H1 heading from markdown content."""
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return "(untitled)"


def extract_date(content, filename=None):
    """Extract ISO date from filename or content (first 20 lines)."""
    if filename:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", str(filename))
        if m:
            return m.group(1)
    for line in content.split("\n")[:20]:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", line)
        if m:
            return m.group(1)
    return None


def extract_doc_metadata(content, filename=None):
    """Extract date and projects from session doc frontmatter-style fields."""
    date_val = extract_date(content, filename)
    projects = ""
    for line in content.split("\n")[:20]:
        if line.startswith("**Projects**:"):
            projects = line.split(":", 1)[1].strip().strip("*")
    return date_val, projects


# ---------------------------------------------------------------------------
# Path utilities
# ---------------------------------------------------------------------------

def relative_doc_path(filepath):
    """Return a doc path relative to ROOT, matching index format."""
    fp = Path(filepath).resolve()
    # Try relative to ROOT/docs first
    try:
        return str(fp.relative_to(ROOT / "docs"))
    except ValueError:
        pass
    # Try relative to ROOT/data
    try:
        return str(fp.relative_to(ROOT / "data"))
    except ValueError:
        pass
    # Try relative to ROOT
    try:
        return str(fp.relative_to(ROOT))
    except ValueError:
        return str(fp)


def relative_path(filepath):
    """Return path relative to ROOT."""
    try:
        return str(Path(filepath).relative_to(ROOT))
    except ValueError:
        return str(filepath)
