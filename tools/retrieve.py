#!/usr/bin/env python3
"""Token-budgeted progressive retrieval from Mogoj's local SQLite index."""

import argparse
import json
import math
import re
import sqlite3
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    ROOT, DB_PATH, PrereqError, add_root_arguments, report_root, mogoj_main,
)
from config import (  # noqa: E402
    RETRIEVAL_TOKEN_BUDGET, CHARS_PER_TOKEN, MAX_SNIPPET_CHARS,
)


def estimate_tokens(text):
    return max(1, math.ceil(len(text) / CHARS_PER_TOKEN)) if text else 0


def _fts_query(query):
    terms = re.findall(r"[\w-]+", query, flags=re.UNICODE)
    if not terms:
        raise ValueError("query must contain at least one searchable word")
    return " AND ".join('"' + term.replace('"', '""') + '"' for term in terms)


def _source_path(indexed_path):
    for candidate in (ROOT / "docs" / indexed_path, ROOT / "data" / indexed_path, ROOT / indexed_path):
        if candidate.is_file():
            return candidate
    return None


def _best_snippet(content, query, max_chars):
    """Return one bounded passage and stable one-based line range."""
    lines = content.splitlines()
    terms = [term.lower() for term in re.findall(r"[\w-]+", query)]
    best_index = 0
    best_hits = -1
    for index, line in enumerate(lines):
        lowered = line.lower()
        hits = sum(lowered.count(term) for term in terms)
        if hits > best_hits:
            best_hits = hits
            best_index = index
    start = max(0, best_index - 1)
    end = min(len(lines), best_index + 2)
    snippet = "\n".join(lines[start:end]).strip()
    if len(snippet) > max_chars:
        snippet = snippet[: max(0, max_chars - 1)].rstrip() + "…"
    return snippet, start + 1, end


def _recency_bonus(created_date):
    if not created_date:
        return 0.0
    try:
        age = max(0, (date.today() - date.fromisoformat(created_date[:10])).days)
    except ValueError:
        return 0.0
    return 0.25 / (1 + age / 30)


def retrieve(query, token_budget=RETRIEVAL_TOKEN_BUDGET, char_budget=None,
             result_limit=8, type_filter=None, project=None, after=None,
             min_score=0.0, include_full=False):
    """Return a bounded three-layer context packet and result metadata."""
    if not DB_PATH.is_file():
        raise PrereqError("SQLite index not found. Run 'mogoj rebuild' first.")
    if token_budget < 1:
        raise ValueError("token_budget must be positive")
    budget = char_budget if char_budget is not None else token_budget * CHARS_PER_TOKEN
    if budget < 1:
        raise ValueError("char_budget must be positive")

    sql = [
        "SELECT d.path, d.title, d.doc_type, d.created_date,",
        "       f.content, bm25(docs_fts) AS bm25_score",
        "FROM docs_fts f JOIN docs d ON d.id = f.rowid",
        "WHERE docs_fts MATCH ?",
    ]
    params = [_fts_query(query)]
    if type_filter:
        sql.append("AND d.doc_type = ?")
        params.append(type_filter)
    if project:
        sql.append("AND (d.path LIKE ? OR d.title LIKE ?)")
        params.extend([f"%{project}%", f"%{project}%"])
    if after:
        sql.append("AND d.created_date >= ?")
        params.append(after)
    sql.append("ORDER BY bm25_score LIMIT ?")
    params.append(max(result_limit * 3, result_limit))

    connection = None
    try:
        connection = sqlite3.connect(str(DB_PATH))
        rows = connection.execute("\n".join(sql), params).fetchall()
    except sqlite3.OperationalError as exc:
        raise PrereqError(f"Search index is unavailable; run 'mogoj rebuild': {exc}") from exc
    finally:
        if connection is not None:
            connection.close()

    ranked = []
    for rank, (path, title, doc_type, created, content, raw_bm25) in enumerate(rows, start=1):
        relevance = 1.0 / rank
        score = relevance + _recency_bonus(created)
        if score < min_score:
            continue
        source = _source_path(path)
        citation_path = source.relative_to(ROOT).as_posix() if source else Path(path).as_posix()
        snippet, line_start, line_end = _best_snippet(content, query, MAX_SNIPPET_CHARS)
        ranked.append({
            "path": citation_path,
            "title": title or "(untitled)",
            "type": doc_type or "general",
            "date": created,
            "score": round(score, 4),
            "bm25": raw_bm25,
            "estimated_full_tokens": estimate_tokens(content),
            "snippet": snippet,
            "line_start": line_start,
            "line_end": line_end,
            "content": content,
        })
    ranked.sort(key=lambda item: (-item["score"], item["path"]))
    ranked = ranked[:result_limit]

    chunks = []
    used = 0

    def append(chunk):
        nonlocal used
        separator = 2 if chunks else 0
        if used + separator + len(chunk) > budget:
            return False
        chunks.append(chunk)
        used += separator + len(chunk)
        return True

    if not ranked:
        message = f"No result met the retrieval threshold for: {query}"
        append(message[:budget])
    else:
        append(f"# Mogoj context: {query}")
        append("## Compact index")
        included = []
        for item in ranked:
            compact = (
                f"- [{item['path']}] — {item['title']} | {item['type']} | "
                f"{item['date'] or 'undated'} | ~{item['estimated_full_tokens']} tokens"
            )
            if append(compact):
                included.append(item)
        if included and append("## Ranked snippets"):
            for item in included:
                citation = f"[{item['path']}:L{item['line_start']}-L{item['line_end']}]"
                block = f"{citation}\n{item['snippet']}"
                append(block)
        if include_full and included and append("## Full documents (explicitly requested)"):
            for item in included:
                append(f"[{item['path']}:L1]\n{item['content']}")

    context = "\n\n".join(chunks)
    public_results = [{k: v for k, v in item.items() if k not in ("content", "snippet")} for item in ranked]
    return {
        "query": query,
        "context": context,
        "context_chars": len(context),
        "estimated_tokens": estimate_tokens(context),
        "char_budget": budget,
        "token_budget": token_budget,
        "within_budget": len(context) <= budget,
        "results": public_results,
    }


@mogoj_main
def main():
    parser = argparse.ArgumentParser(description="Budgeted progressive memory retrieval")
    add_root_arguments(parser)
    parser.add_argument("query")
    parser.add_argument("--budget-tokens", type=int, default=RETRIEVAL_TOKEN_BUDGET)
    parser.add_argument("--budget-chars", type=int)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--type", dest="type_filter")
    parser.add_argument("--project")
    parser.add_argument("--after")
    parser.add_argument("--min-score", type=float, default=0.0)
    parser.add_argument("--full", action="store_true", help="Include full docs only when they fit")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report_root(args)
    result = retrieve(
        args.query, token_budget=args.budget_tokens, char_budget=args.budget_chars,
        result_limit=args.limit, type_filter=args.type_filter, project=args.project,
        after=args.after, min_score=args.min_score, include_full=args.full,
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(result["context"])
        print(
            f"\n[{result['estimated_tokens']} estimated tokens; "
            f"{result['context_chars']}/{result['char_budget']} chars]",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
