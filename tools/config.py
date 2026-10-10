#!/usr/bin/env python3
"""
Mogoj Config — central configuration using configparser (stdlib).

Optional config.ini at repo root. Missing file = use defaults matching
current hardcoded values. Missing keys = use defaults.
"""

import configparser
import os
from pathlib import Path


def _find_config():
    """Find config without coupling memory to the tool checkout."""
    explicit = os.environ.get("MOGOJ_CONFIG")
    if explicit:
        cfg = Path(explicit).expanduser()
        return cfg if cfg.is_file() else None

    root = os.environ.get("MOGOJ_ROOT")
    if root:
        cfg = Path(root).expanduser() / "config.ini"
        return cfg if cfg.is_file() else None

    for candidate in (Path.cwd(), *Path.cwd().parents):
        if (candidate / ".mogoj" / "store.json").is_file():
            cfg = candidate / "config.ini"
            return cfg if cfg.is_file() else None
    return None


_parser = configparser.ConfigParser()
_config_path = _find_config()
if _config_path:
    _parser.read(str(_config_path))


def _get(section, key, fallback, cast=str):
    raw = _parser.get(section, key, fallback=str(fallback))
    return cast(raw)


def _getbool(section, key, fallback):
    return _parser.getboolean(section, key, fallback=fallback)


# --- Paths ---
SCAN_DIRS_REL = _get("paths", "scan_dirs", "docs,data/sessions").split(",")

# --- Index ---
MAX_KEYWORDS_PER_DOC = _get("index", "max_keywords_per_doc", 20, int)
MIN_KEYWORD_LENGTH = _get("index", "min_keyword_length", 3, int)
FINGERPRINT_LENGTH = _get("index", "fingerprint_length", 12, int)
HASH_LENGTH = _get("index", "hash_length", 8, int)

# --- RAM ---
RAM_MAX_LINES = _get("ram", "max_lines", 35, int)
RAM_MAX_BYTES = _get("ram", "max_bytes", 1536, int)
AUTO_ARCHIVE = _getbool("ram", "auto_archive", True)

# --- Search ---
CONTEXT_LINES = _get("search", "context_lines", 1, int)
MAX_RESULTS = _get("search", "max_results", 50, int)
RETRIEVAL_TOKEN_BUDGET = _get("search", "retrieval_token_budget", 1200, int)
CHARS_PER_TOKEN = _get("search", "chars_per_token", 4, int)
MAX_SNIPPET_CHARS = _get("search", "max_snippet_chars", 480, int)

# --- Health ---
STALE_DAYS = _get("health", "stale_days", 30, int)
