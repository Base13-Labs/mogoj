---
name: mogoj-search
description: Perform a targeted follow-up recall from local Mogoj memory. Relevant bounded memory is normally injected automatically with each prompt; use this skill when a deeper or differently phrased search is needed.
---

# Recall local memory

Resolve the installed plugin root as the directory two levels above this `SKILL.md`. Run `node "<plugin-root>/hooks/run.cjs" cli --json search "<focused query>"`. Use the returned bounded `context`; preserve each `path:Lx-Ly` citation when answering. If results are weak, refine the query or use `--project`/`--type`. Do not load full documents unless the user asks and the extra context is necessary. Do not assume a globally installed `mogoj` command exists.

If the database is missing, tell the user to run `mogoj rebuild`. Never substitute an unrelated repository or upload memory to an external service.
