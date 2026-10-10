---
name: mogoj-search
description: Recall relevant local Mogoj memory as bounded snippets with Markdown source citations. Use for questions about prior decisions, projects, people, or recent context.
---

# Recall local memory

Run `mogoj --json search "<focused query>"`. Use the returned bounded `context`; preserve each `path:Lx-Ly` citation when answering. If results are weak, refine the query or use `--project`/`--type`. Do not load full documents unless the user asks and the extra context is necessary.

If the database is missing, tell the user to run `mogoj rebuild`. Never substitute an unrelated repository or upload memory to an external service.
