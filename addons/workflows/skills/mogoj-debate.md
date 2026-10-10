# Mogoj Debate — Structured Multi-AI Debate

Run a structured multi-round debate between Claude (you) and Codex CLI on a document, architecture decision, or strategy question. Both AIs challenge each other until they converge on a final position.

## Arguments

`$ARGUMENTS` is the topic or question to debate. If empty, ask the user what to debate.

Examples:
- `/mogoj-debate Should we use Supabase or Firebase for the new project?`
- `/mogoj-debate Review droids/plan.md and challenge every assumption`
- `/mogoj-debate Is our pricing strategy for ChatX correct?`

## Step 0: Locate Memory Store

Use the store resolved by the `mogoj` CLI. Save debate outcomes only when the user explicitly asks.

### Pre-flight

Check that `codex` CLI is available:
```bash
which codex
```
If not found, tell the user to install it (`npm i -g @openai/codex`) and stop.

## Step 1: Form Your Position

Read any files the user referenced or that are relevant to the topic. Analyze the question and form a clear position with specific reasoning — not vague opinions. Structure your take as numbered points with explicit pros/cons.

## Step 2: Run Debate Rounds

Execute 2-4 rounds of debate. Each round follows this pattern:

**Your turn (Claude):**
- State your position clearly with numbered arguments
- Acknowledge where the other side might be right
- Ask specific challenge questions

**Codex's turn:**
- Send your position to Codex via `codex exec` with `--full-auto` flag
- Include the working directory context: `-C {repo_root}`
- Save each round's output to a file for reference
- Set a 5-minute timeout

Template for calling Codex:
```bash
cat <<'PROMPT' | codex exec --full-auto -C {repo_root} -o {output_file} -
{Context: what files to read, what the debate is about}

## Round {N} — Claude's Position

{Your numbered arguments}

---

Your job: Challenge every point above. Where is Claude wrong? What is Claude missing?
Give your counter-position on each point, then state which ones you agree with and which you'd change.
{If round > 1: "Can we converge? Give final positions on each point."}
PROMPT
```

**Between rounds:**
- Read Codex's response
- Update your position based on valid challenges
- Concede where Codex is right — don't be stubborn
- Push back where you have evidence

**Convergence signals (stop debating when):**
- Both sides agree on all major points
- Remaining disagreements are preference, not substance
- 4 rounds reached without convergence (summarize the split)

## Step 3: Write Convergence Doc

After the debate concludes, write a convergence summary. Save it to:
`$MOGOJ_ROOT/docs/decisions/{date}-{topic-slug}.md`

Format:
```markdown
# Debate: {Topic}

**Date**: {YYYY-MM-DD}
**Participants**: Claude (Opus) + Codex (GPT)
**Rounds**: {N}
**Status**: Converged | Split on {X}

## Final Decisions

| Question | Decision | Who Won | Confidence |
|----------|----------|---------|------------|
| {point}  | {answer} | {Claude/Codex/Both} | {High/Medium/Low} |

## Key Insights

{Bulleted list of the most valuable things that emerged from the debate — things neither AI would have reached alone.}

## Remaining Disagreements

{If any points didn't converge, list them with both positions.}

## Round History

{Brief summary of how positions evolved across rounds.}
```

## Step 4: Update Related Docs

If the debate changes any existing decisions or plans:
- Update the relevant project brief in `$MOGOJ_ROOT/docs/projects/`
- Update `$MOGOJ_ROOT/docs/company/shared-handoff.md` if it affects current state
- Only update files that exist — don't create new project briefs

## Step 5: Report

Print a summary:
```
Debate Complete — {topic}

Rounds: {N}
Status: {Converged / Split}

Decisions:
  {numbered list of final positions}

Saved to: {file path}
```

## Constraints

- Never fake Codex's responses — always actually call `codex exec`
- Never agree with Codex just to end the debate — push back when you have evidence
- Never exceed 4 rounds — if no convergence, document the split
- Always save debate artifacts — the reasoning history is valuable
- If Codex is unavailable or errors, report the error and offer to continue as a solo analysis
- Mark any uncertain conclusions with `[Uncertain]` tags
- Keep each round focused — don't let scope creep into unrelated topics
