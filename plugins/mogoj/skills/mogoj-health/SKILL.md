---
name: mogoj-health
description: Diagnose Mogoj configuration, permissions, SQLite FTS5, index drift, and agent integration readiness. Use when installation or recall is not working.
---

# Diagnose Mogoj

Run `mogoj --json doctor` and explain failing or warning checks in plain language. Recommend only the recovery command indicated by the result. Do not rebuild, migrate, change permissions, or install integrations unless the user asks; diagnosis is read-only.
