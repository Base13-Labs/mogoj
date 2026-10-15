---
name: mogoj-save
description: Save a durable decision, project fact, or user-requested note immediately. Mogoj normally checkpoints meaningful outcomes automatically; use this skill when the user explicitly asks to remember something now.
---

# Save local memory

Condense the requested durable information without adding secrets or speculative claims. Resolve the installed plugin root as the directory two levels above this `SKILL.md`. Run `node "<plugin-root>/hooks/run.cjs" cli save "<content>" --title "<short title>" --type <note|project|decision|company|person>`. If the CLI reports a possible secret, stop and let the user choose `--redact`; never use `--allow-secrets` without explicit authorization. Do not assume a globally installed `mogoj` command exists.

Report the returned store-relative path. Do not edit the store directly. Automatic mode separately checkpoints meaningful completed work; do not create a duplicate manual memory for the same outcome.
