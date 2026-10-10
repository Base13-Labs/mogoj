# Mogoj — Show All Commands

List all available Mogoj and project commands with descriptions.

## Step 0: Locate Memory Store

Use `mogoj --json status` and `mogoj --json doctor` to inspect the configured store.

## Instructions

Find all Mogoj skills by running:
```bash
mogoj --json status
```

Also find any project-specific skills:
```bash
ls ~/.claude/commands/b13-*.md 2>/dev/null
```

For each file found, read the first line (the `# Title`) and the first paragraph to extract what it does.

Then display a clean table:

```
Mogoj Memory System
══════════════════════

Command                     | Description
----------------------------|-----------------------------------------
/mogoj-save                 | Persist session to memory (index + RAM)
/mogoj-search               | Search across all memory
/mogoj-show                 | This command — list all commands
...                         | ...

Project Commands (b13-*)
══════════════════════════

Command                     | Description
----------------------------|-----------------------------------------
/b13-init                   | ...
...                         | ...
```

Also show memory system stats:
```
Memory Stats
════════════
Sessions saved: {count files in $MOGOJ_ROOT/data/sessions/ recursively}
Index keywords: {count entries in $MOGOJ_ROOT/data/index/context-index.md}
RAM status: {Active / Empty}
```

Keep descriptions to one line (~60 chars max). Sort alphabetically.

Do NOT suggest running any commands. Just display the tables.
