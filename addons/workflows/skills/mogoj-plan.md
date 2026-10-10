# Mogoj Plan — Generate Task List

Analyze a project, understand what needs to be done, and generate a structured task list that `/run-tasks` can execute autonomously.

## Instructions

You are a senior engineer planning all the work for a project. Your output is a `tasks/todo.md` file formatted so that `/run-tasks` can pick up each task and implement it without human input.

### Step 1: Understand the Project

Read these files to build context (skip any that don't exist):

1. `CLAUDE.md` — project AI rules and constraints
2. `PROJECT_RULES.md` — product truth and priorities
3. `lessons.local.md` — known footguns
4. `package.json` / `app.json` / `Cargo.toml` — tech stack
5. `docs/PRE_RELEASE_CHECKLIST.md` — if it exists, these are known blockers
6. `tasks/todo.md` — if it exists, check what's already done vs pending
7. `README.md` — project overview

Then do a quick scan of the codebase:
- List `src/` directory structure (screens, services, components)
- Check for `TODO`, `FIXME`, `PLACEHOLDER`, `HACK` markers in code
- Check for any `.env.example` or missing config patterns

### Step 2: Ask Clarifying Questions (if needed)

If the project's goals or next milestone is unclear, ask the user **at most 3 questions**:

1. "What's the next milestone?" (e.g., "ship to TestFlight", "add payments", "v2 launch")
2. "Any specific areas to focus on?" (e.g., "security hardening", "new features", "performance")
3. "Anything explicitly out of scope right now?"

If `$ARGUMENTS` is provided, treat it as the milestone/focus description and skip questions.

If the project has a clear `PRE_RELEASE_CHECKLIST.md` or existing `todo.md` with pending items, you may have enough context to skip questions entirely. Use judgment.

### Step 3: Generate Task Categories

Group tasks into categories based on what you found. Common categories:

- **Security & Hardening** — RLS, auth, secrets, env vars
- **Core Features** — new functionality the product needs
- **UX Polish** — improvements to existing flows
- **Infrastructure** — CI/CD, builds, deploys, config
- **Cost Optimization** — reducing API costs, caching
- **Tech Debt** — refactors, test coverage, cleanup
- **Pre-Release** — final items before shipping

Order categories by priority (ship-blocking first, nice-to-have last).

### Step 4: Write Task List

Write to `tasks/todo.md` using this exact format:

```markdown
# [Project Name] — Task List

Last updated: [TODAY'S DATE]

Milestone: **[milestone name]**

---

## [Category Name]

### [ID]. [Task Title]
- [Clear description of what to do]
- [Specific files to touch, if known]
- [Definition of done]
- **Scope**: [small / medium / large]
- **Type**: code | user-action | research
```

#### Task ID Format
Use a category prefix + number:
- `S1, S2...` — Security
- `F1, F2...` — Features
- `U1, U2...` — UX
- `I1, I2...` — Infrastructure
- `C1, C2...` — Cost
- `D1, D2...` — Tech Debt
- `R1, R2...` — Pre-Release

#### Critical Rules for Task Writing

1. **Each task must be completable by `/run-tasks` in one shot.** If a task is too big, break it into smaller tasks. A good task touches 1-3 files and has a clear "done" state.

2. **Include enough context that an agent can implement without asking questions.** Mention specific file paths, function names, expected behavior. The agent reading this has no conversation history.

3. **Mark user-action tasks clearly.** Tasks requiring external service setup (OAuth, API keys, App Store) should be marked `user-action` — `/run-tasks` will skip these and move on.

4. **Order tasks within each category by dependency.** If task S2 depends on S1, list S1 first. `/run-tasks` executes top-to-bottom.

5. **Preserve completed tasks.** If an existing `todo.md` has completed tasks (marked with `[x]`, `~~strikethrough~~`, or `DONE`), keep them in the file for history. Add new tasks below or in appropriate categories.

6. **Scope estimates matter.** `small` = 1 file, <30 lines changed. `medium` = 2-4 files, <100 lines. `large` = 5+ files or architectural change. Prefer breaking `large` into multiple `medium` tasks.

7. **No vague tasks.** Bad: "Improve error handling." Good: "Route 17 console.log calls in src/ through ErrorReporting.log() — files: StorageService.ts, RecordScreen.tsx, OfflineQueue.ts"

### Step 5: Summary

After writing the task file, print:

```
Task Plan Complete — [project-name]

Milestone: [milestone]
Categories: [count]
Total tasks: [count]
  Code tasks: [count] (run-tasks can handle these)
  User-action: [count] (needs your involvement)
  Research: [count] (needs investigation first)

Run `/run-tasks` to start executing code tasks automatically.
Run `/run-tasks [ID]` to execute a specific task.
```

## Boundaries

- Do NOT implement any tasks — only plan them
- Do NOT modify code files — only create/update `tasks/todo.md`
- Do NOT delete completed tasks from existing task files
- If an existing `tasks/todo.md` has pending tasks, ask the user: "There are [N] pending tasks. Should I regenerate the full list, or add new tasks alongside existing ones?"
