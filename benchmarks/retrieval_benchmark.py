#!/usr/bin/env python3
"""Compare naive, keyword, and progressive retrieval payload sizes."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--query", action="append", required=True)
    parser.add_argument("--budget-tokens", type=int, default=1200)
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    markdown = list((root / "docs").rglob("*.md")) + list((root / "data" / "sessions").rglob("*.md"))
    naive_chars = sum(len(path.read_text(errors="replace")) for path in markdown)
    tool = Path(__file__).resolve().parents[1] / "tools" / "retrieve.py"
    env = os.environ.copy()
    env["MOGOJ_ROOT"] = str(root)
    rows = []
    for query in args.query:
        completed = subprocess.run(
            [sys.executable, str(tool), query, "--budget-tokens", str(args.budget_tokens), "--json"],
            env=env, check=True, text=True, stdout=subprocess.PIPE,
        )
        result = json.loads(completed.stdout)
        keyword_chars = sum(
            len(path.read_text(errors="replace"))
            for path in markdown if query.lower() in path.read_text(errors="replace").lower()
        )
        rows.append({
            "query": query,
            "naive_chars": naive_chars,
            "keyword_chars": keyword_chars,
            "progressive_chars": result["context_chars"],
            "progressive_estimated_tokens": result["estimated_tokens"],
            "results": len(result["results"]),
            "within_budget": result["within_budget"],
        })
    print(json.dumps(rows, indent=2))


if __name__ == "__main__":
    main()
