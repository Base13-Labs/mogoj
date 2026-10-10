---
name: mogoj-status
description: Inspect the configured Mogoj store, recent memories, and index readiness. Use for setup checks and lightweight memory-status questions.
---

# Inspect memory status

Run `mogoj --json status`. Use `mogoj --json recent` only when the user asks what changed recently. Explain missing database state with the copy-paste recovery command `mogoj rebuild`. These operations are read-only.
