---
name: mogoj-save
description: Save a durable decision, project fact, or user-requested note immediately. Mogoj normally checkpoints meaningful outcomes automatically; use this skill when the user explicitly asks to remember something now.
---

# Save local memory

Condense the requested durable information without adding secrets or speculative claims. In Claude Code, run `node "${CLAUDE_PLUGIN_ROOT}/plugins/mogoj/hooks/run.cjs" cli save "<content>" --title "<short title>" --type <note|project|decision|company|person>`. In Codex or another portable integration, run `mogoj save "<content>" --title "<short title>" --type <type>`. If the CLI reports a possible secret, stop and let the user choose `--redact`; never use `--allow-secrets` without explicit authorization.

Report the returned store-relative path. Do not edit the store directly. Automatic mode separately checkpoints meaningful completed work; do not create a duplicate manual memory for the same outcome.
