---
name: mogoj-save
description: Save a durable decision, project fact, or user-requested note to the configured local Mogoj store. Use only when the user asks to remember or persist information.
---

# Save local memory

Condense the requested durable information without adding secrets or speculative claims. Run `mogoj save "<content>" --title "<short title>" --type <note|project|decision|company|person>`. If the CLI reports a possible secret, stop and let the user choose `--redact`; never use `--allow-secrets` without explicit authorization.

Report the returned store-relative path. Do not edit the store directly or infer permission to save unrelated conversation content.
