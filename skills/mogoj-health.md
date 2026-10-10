# Mogoj Health — Memory System Diagnostics

Run health checks on the SupaMogoJ memory system and help fix issues.

## Workflow

### Step 1: Run full health check

```bash
python3 tools/health.py check
```

Read the output. Each line is one of:
- `[OK]` — check passed
- `[INFO]` — informational, no action needed
- `[WARN]` — issue that should be addressed
- `[FIXED]` — auto-fixed (only with `--fix`)

### Step 2: Report findings

Display the health report to the user in a clean format. Group by severity:
1. Warnings (need attention)
2. Info (awareness)
3. OK (passed)

### Step 3: Offer fixes

For each warning, explain what it means and offer to fix:

| Issue | Fix |
|-------|-----|
| Orphan keywords | `python3 tools/health.py check --fix` (auto-removes) |
| Duplicate mappings | `python3 tools/health.py check --fix` (auto-dedupes) |
| Stale docs | Review manually — may need update or archival |
| Broken cross-refs | Fix the markdown links manually |
| Missing people profiles | Create `docs/people/{name}.md` |
| RAM placeholders | Run `/mogoj-save` with `--auto` to populate |
| Index/DB drift | `python3 tools/db.py sync` |

### Step 4: Targeted checks (optional)

If user wants details on specific areas:
- `python3 tools/health.py stale --days 14` — show docs older than 14 days
- `python3 tools/health.py orphans` — list all orphan keywords
- `python3 tools/health.py people` — show missing person profiles
- `python3 tools/health.py refs` — show all broken references

### Step 5: Confirm

After fixes are applied, re-run:
```bash
python3 tools/health.py check
```

Report final status.

## Boundaries

- Do NOT modify docs without explicit user confirmation
- Do NOT delete keyword mappings without running `--fix` first to preview
- Do NOT create people profiles automatically — only suggest them
- Auto-fixable issues (orphans, duplicates) are safe to fix with `--fix`
