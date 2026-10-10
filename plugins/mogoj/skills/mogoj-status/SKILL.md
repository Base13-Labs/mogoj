---
name: mogoj-status
description: Inspect the configured Mogoj store, recent memories, and index readiness. Use for setup checks and lightweight memory-status questions.
---

# Inspect memory status

In Claude Code, run `node "${CLAUDE_PLUGIN_ROOT}/plugins/mogoj/hooks/run.cjs" cli --root "${user_config.memory_path}" --json status`. In Codex or another portable integration, run `mogoj --json status`. Use the equivalent `--json recent` command only when the user asks what changed recently. Explain missing database state; automatic mode normally initializes and synchronizes it at session start. These operations are read-only.
