# Mogoj Search — Search Memory

Search across all stored memory — sessions, decisions, projects, and the context index.

## Arguments

`$ARGUMENTS` is the search query. If empty, ask what to search for.

Examples:
- `/mogoj-search chatx pricing` — find all docs mentioning chatX pricing
- `/mogoj-search --keyword sales` — look up "sales" in the context index
- `/mogoj-search --recent 5` — show 5 most recent sessions

## Step 0: Locate Memory Store

The memory store is at `$MOGOJ_ROOT`. If unset, default to `~/code/brain/`. All paths below are relative to this root.

Determine the mogoj tools location: check `$MOGOJ_TOOLS` first, then `~/code/mogoj/tools/`, then look for a `tools/` directory at `$MOGOJ_ROOT`.

## Instructions

### Mode 1: Keyword Lookup (--keyword or -k)

If the query starts with `--keyword` or `-k`:

1. Read `$MOGOJ_ROOT/data/index/context-index.md`
2. Find the keyword entry
3. List all linked docs with one-line summaries
4. Show second-degree connections (docs that share other keywords with the matched docs)

Display:
```
Keyword: {keyword}

Direct matches:
  - {doc_path} — {one-line summary}
  - {doc_path} — {one-line summary}

Related (shared keywords):
  - {doc_path} — via: {shared_keywords}
```

### Mode 2: Recent Sessions (--recent or -r)

If the query starts with `--recent` or `-r`:

1. List all session files in `$MOGOJ_ROOT/data/sessions/` sorted by date (newest first)
2. Show the requested count (default 10)
3. For each, show date, title, and projects touched

Display:
```
Recent Sessions

Date       | Title                              | Projects
-----------|------------------------------------|----------------
2026-04-19 | Career Direction & Idea Review     | General, chatX
...        | ...                                | ...
```

### Mode 3: Full-Text Search (default)

For any other query:

1. Search all `.md` files in `$MOGOJ_ROOT/docs/` and `$MOGOJ_ROOT/data/` for the query
2. Use the Grep tool with the query as pattern
3. Group results by file, show matching lines with context
4. Also check the context index for keyword matches

Display:
```
Search: "{query}"

{file_path} ({match_count} matches)
  L{line}: {matching line with context}
  L{line}: {matching line with context}

{file_path} ({match_count} matches)
  L{line}: {matching line with context}

Index keywords matching: {list of keyword matches, if any}
```

### Step 2: Offer Follow-up

After showing results, ask:
```
Want to read any of these docs? Give me a number or path.
```

## Constraints

- Search memory store only (`$MOGOJ_ROOT/`)
- Never modify files — read-only operation
- If no results found, suggest alternative keywords from the index
- Try to run `python3 $MOGOJ_TOOLS/search.py "{query}"` first if the script exists — fall back to Grep if not
