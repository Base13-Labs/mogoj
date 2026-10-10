# Mogoj — AGENTS.md

Portable memory system for AI agents. This repo contains the engine — skills (slash commands) and tools (Python CLI).

## What This Repo Is

This is the **engine**, not the data store. It contains:
- `skills/` — slash commands for Claude Code (symlinked to `~/.claude/commands/`)
- `tools/` — Python CLI scripts for memory operations
- `template/` — empty directory structure for initializing new memory stores

Your actual memory data lives in a separate initialized store (default: `~/.mogoj`), optionally configured via `$MOGOJ_ROOT` or `mogoj --root PATH`.

## Agent Rules

If you're working in this repo, you're modifying the engine itself. Rules:
1. All Python tools must use stdlib only — no pip dependencies
2. Skills must reference `$MOGOJ_ROOT` for data paths, not hardcoded paths
3. The `find_repo_root()` pattern in tools walks up from cwd to find the data store
4. Keep skills self-contained — each .md file is a complete instruction set
5. Template files in `template/` are copied on init — keep them minimal

## How Skills Work

Each `.md` file in `skills/` is a Claude Code slash command. When symlinked to `~/.claude/commands/`, typing `/mogoj-save` loads that file as instructions for the agent.

Skills locate the memory store via:
1. `$MOGOJ_ROOT` env var
2. A validated `.mogoj/store.json` marker in the current directory or its parents
3. The initialized `~/.mogoj` default
