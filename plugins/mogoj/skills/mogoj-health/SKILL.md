---
name: mogoj-health
description: Diagnose Mogoj configuration, permissions, SQLite FTS5, index drift, and agent integration readiness. Use when installation or recall is not working.
---

# Diagnose Mogoj

In Claude Code, run `node "${CLAUDE_PLUGIN_ROOT}/plugins/mogoj/hooks/run.cjs" cli --json doctor`. In Codex or another portable integration, run `mogoj --json doctor`. Explain failing or warning checks in plain language. Recommend only the recovery action indicated by the result. Do not migrate, change permissions, or install integrations unless the user asks; diagnosis is read-only.
