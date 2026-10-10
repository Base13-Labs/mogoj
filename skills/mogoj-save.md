# Mogoj Save — Persist Session to Memory

Save the current conversation as a structured doc, update the context index, refresh RAM, then offer continuation mode. Works from any repo.

## Arguments

`$ARGUMENTS` can be:
- *(empty)* — save, then ask which continuation mode
- `clean` — save, then compact context
- `reload` — save, then compact + reload saved doc
- `continue` — save, update index + RAM, keep working (no compact, no fresh start)

## Step 0: Locate Memory Store

Use the installed `mogoj` CLI, which safely resolves the configured store. Prefer `mogoj save` over writing files directly.

## Step 1: Determine Save Location

Figure out the best subdirectory based on what was discussed:

- If the conversation was primarily about a **specific project** → `$MOGOJ_ROOT/data/sessions/{project-slug}/{date}-{topic-slug}.md`
- If it was about a **decision** → `$MOGOJ_ROOT/docs/decisions/{date}-{topic-slug}.md` (and also save a session doc)
- If it was about **company/strategy** → `$MOGOJ_ROOT/data/sessions/company/{date}-{topic-slug}.md`
- If it was **general/mixed** → `$MOGOJ_ROOT/data/sessions/{date}-{topic-slug}.md`

Use today's date in `YYYY-MM-DD` format. The topic slug should be 2-4 words max (e.g., `chatx-pricing-strategy`, `apollo-outreach-setup`).

Create the directory if it doesn't exist.

## Step 2: Write the Session Doc

Write the session doc with this structure:

```markdown
# {Descriptive Title}

**Date**: {YYYY-MM-DD}
**Repo**: {the repo the conversation took place in, e.g. `chatX`, `dwight`, `brain`}
**Context**: {one-line description of what triggered this conversation}
**Projects**: {comma-separated list of projects touched, or "General"}

## Key Points

{Bulleted list of the most important things discussed, decided, or learned. Be specific and actionable — not vague summaries. Include concrete details like names, numbers, URLs, strategies.}

## Decisions Made

{Bulleted list of any decisions reached during the conversation. If none, omit this section.}

## Open Questions / Next Steps

{Bulleted list of unresolved items or next actions. If none, omit this section.}

## Raw Notes

{More detailed capture of the conversation content — key exchanges, reasoning, context that might be useful later. Not a full transcript, but enough that a future agent can reconstruct the conversation's value. Include code snippets, commands, or configurations if relevant.}
```

**Guidelines:**
- Focus on **operational value** — what would a future agent or the user need to know?
- Include specific details: numbers, names, URLs, file paths, strategies
- Skip small talk, greetings, and meta-discussion about the conversation itself
- If the conversation was very short or trivial, keep the doc proportionally short
- Note which repo/codebase the work happened in so future agents know where to look

## Step 3: Update Context Index

Open `$MOGOJ_ROOT/data/index/context-index.md` and add keyword entries for this session. Rules:

- **Multiple keywords per doc** — extract 3-10 relevant keywords from the conversation
- Insert each keyword alphabetically into the existing index
- If keyword already exists, append the new doc path to its list
- Mark killed/archived items with `[killed]` or `[archived]` tags
- Keywords should be specific enough to be useful but general enough to connect related conversations
- Use lowercase, hyphenated slugs (e.g., `sales-sprint`, `meta-ads`, `moonlighting`)

Also run `python3 $MOGOJ_TOOLS/index.py add <keyword> <doc_path>` for each new keyword if the script exists, to keep JSON in sync.

## Step 4: Update RAM

Overwrite `$MOGOJ_ROOT/data/ram/current.md` with current session state:

```markdown
# RAM — Active Session Memory

**Session**: {date} — {topic}
**Status**: Active

---

## Hot Context (direct — read these first)

{List of docs directly relevant to current conversation — session doc, any modified docs}

## Warm Context (second-degree — follow if needed)

{List of docs one hop away — related projects, prior sessions on same topics}

## Active Threads

{Numbered list of open threads/questions from this session}

## Key Facts This Session

{Bulleted list of concrete facts established or changed this session}

## Unresolved

{Anything left hanging — questions asked but not answered, data needed, etc.}
```

**RAM rules:**
- current.md is always overwritten (not appended) — it's current state only
- If multiple sessions run concurrently, use `data/ram/{session-slug}.md` for each
- When a session is fully done, current.md can be cleared or left as last-session snapshot
- Hot context = docs you'd read first if resuming this conversation
- Warm context = docs you'd read if hot context isn't enough (the "double hash")

## Step 5: Update Cross-References

If relevant project briefs exist in `$MOGOJ_ROOT/docs/projects/`, append a line to their "Sources" or "Sessions" section pointing to this session doc. Only do this if the conversation had substantive project-specific content.

## Step 6: Confirm and Offer Continuation Mode

Display:
```
Mogoj saved.
Session: {file path}
Index: {number} keywords added/updated
RAM: refreshed
```

Then show a brief summary (2-3 lines) of what was captured.

If `$ARGUMENTS` was not provided, ask:
```
1. continue — full memory, nothing changes
2. continue lite — save and read back RAM summary only
```

If `$ARGUMENTS` is `continue`:
- Do nothing. Conversation continues as-is.

If `$ARGUMENTS` is `continue lite`:
- Read back `data/ram/current.md` so active threads and file pointers stay in context
- This is the "where we left off" handoff — no compact, no data loss
