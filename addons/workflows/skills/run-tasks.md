# Autonomous Task Runner

You are an autonomous task executor. Read the project's task file, pick the next incomplete task, implement it, write a report, mark it done, and move to the next task. Do NOT ask the user for input — make assumptions and document them.

## Step 1: Discover Task File

Find the task file in the current project. Check these paths in order:
- `tasks/todo.md`
- `tasks/tasks.md`
- `TODO.md`
- `todo.md`

If `$ARGUMENTS` is provided:
- If it looks like a task ID (e.g., `A1`, `T1`, `M1`, `1`, `P2`), target that specific task only
- If it's a file path, use that as the task file

If no task file is found, tell the user and stop.

## Step 2: Pick Next Task

Read the task file. Find the first task that is NOT marked as done/completed/checked.

Task completion markers to recognize (case-insensitive):
- `[x]`, `[X]` — done
- `~~strikethrough~~` — done
- Lines containing `DONE`, `COMPLETED`, `SHIPPED` — done
- `[ ]`, `- ` without checkbox, unmarked items — NOT done, pick these

If `$ARGUMENTS` specified a task ID, find and use that task instead.

## Step 3: Implement the Task

For each task:

1. **Read the task scope** — understand what needs to be done, the definition of done, and likely files involved
2. **Read the project's conventions** — CLAUDE.md and any referenced rule files are auto-loaded; follow them
3. **Read each relevant file** before modifying it — understand current state
4. **Implement the change**:
   - Make the smallest complete change that satisfies the task
   - Make assumptions for unknowns — document ALL assumptions in the report
   - Use `PLACEHOLDER:` markers only where user input is truly required (API keys, personal preferences, etc.)
   - Follow existing code patterns and conventions
5. **Constraints**:
   - No data-loss changes
   - No privacy footguns
   - No breaking existing functionality
   - If the task is too large, implement the smallest useful slice and note the remainder in the report

## Step 4: Write Report (Background)

After implementing, launch a **background** sonnet sub-agent to write the report:

```
Agent tool call:
  subagent_type: "general-purpose"
  model: "sonnet"
  run_in_background: true
  description: "Write task report"
  prompt: |
    Create the directory docs/reports/ if it doesn't exist, then write a task report file.

    Write to: docs/reports/report_{TASK_ID}.md

    Use this template:
    ---
    # Task Report: {TASK_ID} — {TASK_TITLE}

    **Completed**: {TODAY'S DATE}

    ## Changes
    - {file_path}: {what changed and why}

    ## Assumptions
    - {each assumption made during implementation}

    ## Things to Check
    - [ ] {verification item — things the user should test or review}

    ## Notes
    {any follow-ups, warnings, or remaining work}
    ---

    Here is the data for this report:
    Task ID: {ID}
    Task Title: {TITLE}
    Files changed: {LIST}
    Assumptions made: {LIST}
    Things to verify: {LIST}
    Additional notes: {NOTES}
```

Do NOT wait for the report to finish. Continue to the next task immediately.

## Step 5: Mark Task Done

Update the task file to mark the completed task as done:
- If using checkboxes: change `[ ]` to `[x]`
- If using other format: append ` — DONE` or use the file's existing done convention

## Step 6: Loop

Pick the next incomplete task and repeat from Step 3.

**Stop conditions:**
- No more incomplete tasks remain (the ONLY reason to stop)

**Pacing:**
- After every 3 completed tasks, pause for 60 seconds (`sleep 60`) to let background reports finish and reduce pressure
- After the pause, re-read the task file to pick up any external changes, then continue

**On failure:**
- Write a failure report to `docs/reports/report_{TASK_ID}_FAILED.md` explaining what went wrong, do NOT mark the task as done, skip to the next task
- Failures do NOT count toward the 3-task pacing counter
- Never stop because of a failure — keep going

## Output

After ALL tasks are completed, provide a final summary:
- Tasks completed: {count}
- Tasks failed: {count}
- Tasks remaining: {count}
- Reports written: {list of report file paths}
