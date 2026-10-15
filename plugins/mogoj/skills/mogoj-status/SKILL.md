---
name: mogoj-status
description: Inspect the configured Mogoj store, recent memories, and index readiness. Use for setup checks and lightweight memory-status questions.
---

# Inspect memory status

Resolve the installed plugin root as the directory two levels above this `SKILL.md`. Run `node "<plugin-root>/hooks/run.cjs" cli --json status`. Use the equivalent `--json recent` command only when the user asks what changed recently. Explain missing database state; automatic mode normally initializes and synchronizes it at session start. These operations are read-only. Do not assume a globally installed `mogoj` command exists.
