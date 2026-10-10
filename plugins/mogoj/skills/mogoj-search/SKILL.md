---
name: mogoj-search
description: Perform a targeted follow-up recall from local Mogoj memory. Relevant bounded memory is normally injected automatically with each prompt; use this skill when a deeper or differently phrased search is needed.
---

# Recall local memory

In Claude Code, run `node "${CLAUDE_PLUGIN_ROOT}/plugins/mogoj/hooks/run.cjs" cli --json search "<focused query>"`. In Codex or another portable integration, run `mogoj --json search "<focused query>"`. Use the returned bounded `context`; preserve each `path:Lx-Ly` citation when answering. If results are weak, refine the query or use `--project`/`--type`. Do not load full documents unless the user asks and the extra context is necessary.

If the database is missing, tell the user to run `mogoj rebuild`. Never substitute an unrelated repository or upload memory to an external service.
