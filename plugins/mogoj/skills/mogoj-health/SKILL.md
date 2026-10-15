---
name: mogoj-health
description: Diagnose Mogoj configuration, permissions, SQLite FTS5, index drift, and agent integration readiness. Use when installation or recall is not working.
---

# Diagnose Mogoj

Resolve the installed plugin root as the directory two levels above this `SKILL.md`. Run `node "<plugin-root>/hooks/run.cjs" cli --json doctor`. Explain failing or warning checks in plain language. Recommend only the recovery action indicated by the result. Do not migrate, change permissions, or install integrations unless the user asks; diagnosis is read-only. Do not assume a globally installed `mogoj` command exists.
