# Automatic memory in Claude Code

Mogoj's Claude Code plugin is designed to disappear into normal work. After installation, lifecycle hooks initialize the local store, recall relevant memory before Claude handles a prompt, and checkpoint durable outcomes after meaningful work. The command line remains an internal deterministic engine and an optional advanced interface; users do not need it for everyday Claude Code memory.

## Install once

```bash
claude plugin marketplace add Base13-Labs/mogoj
claude plugin install mogoj@base13-labs
```

Start a new Claude Code session. The plugin defaults to:

- mode: `auto`;
- private store: `~/.mogoj`;
- automatic prompt recall: approximately 500 estimated tokens;
- startup context: approximately 250 estimated tokens;
- no account, API key, remote server, or embedding service.

The first session creates the store and SQLite index automatically. The plugin package contains the runtime, so installing the plugin does not require a separate Mogoj CLI installation.

Installation does not ask the user to choose a mode or memory path. The zero-configuration defaults are `auto` and `~/.mogoj`.

## What happens automatically

### Session start

The `SessionStart` hook:

1. creates the configured store if it does not exist;
2. creates or synchronizes the local SQLite FTS5 index;
3. returns only recent checkpoints that identify the current project;
4. tells Claude that automatic memory is active.

It does not inject the entire store or unrelated project history.

### Each user prompt

The `UserPromptSubmit` hook uses the submitted prompt and current project name to create a focused local query. If useful matches exist, it adds a bounded, source-cited context packet beside the prompt. If nothing matches, it adds nothing. Repeated delivery of the same prompt in one session is suppressed.

### Completed work

The `Stop`, `PreCompact`, and `SessionEnd` hooks look for durable outcomes. In `auto` mode, meaningful work creates a structured Markdown checkpoint containing the user request and Claude's final outcome/handoff. Checkpoints are capped, deduplicated, and scanned for common secret patterns. Short greetings and conversational noise are ignored.

Mogoj stores the final handoff, not the raw transcript. Automatic capture is intentionally conservative but still heuristic; explicitly save critical decisions when exact wording matters.

## Modes

Mogoj starts in `auto` mode. To change it later, edit `~/.mogoj/config.ini` and change `mode` in the `[automation]` section:

```ini
[automation]
mode = confirm
```

| Mode | Recall | Saving |
|---|---|---|
| `auto` | Automatic bounded recall | Automatically saves durable outcomes |
| `confirm` | Automatic bounded recall | Claude asks before saving a detected outcome |
| `manual` | Only targeted skill use | Only when the user explicitly asks |
| `off` | Disabled | Disabled; does not initialize a store |

Use `auto`, `confirm`, `manual`, or `off`. Changes apply on the next hook invocation; restarting Claude Code is the clearest way to begin a session consistently in the new mode. For advanced or temporary overrides, `MOGOJ_AUTOMATION_MODE` changes the mode and `MOGOJ_ROOT` selects a different initialized store path.

## Manual and recovery skills

The plugin still provides four focused skills:

- targeted search when automatic recall needs a different query;
- explicit save when exact wording is important;
- status/recent inspection;
- health diagnostics.

These skills call the runtime inside the installed plugin. Removing the plugin never removes the external memory store.

Lifecycle commands:

```bash
claude plugin update mogoj@base13-labs
claude plugin disable mogoj@base13-labs
claude plugin enable mogoj@base13-labs
claude plugin uninstall mogoj@base13-labs
```

Install optional debate/planning/task workflows separately with `claude plugin install mogoj-workflows@base13-labs`.

## Privacy and token behavior

All search, indexing, and capture operations run locally. Prompt text is used transiently as a local search query and is not logged by Mogoj. When a match exists, the hook deliberately adds the excerpt to Claude's model context; that excerpt is subject to Claude Code's provider and organization data-handling settings. Mogoj makes no separate network request. Saved checkpoints live in `data/sessions/`; automatic state contains only hashes and the latest checkpoint path. Hook failures fail open so a memory problem cannot prevent Claude from working.

Recalled excerpts are labeled as untrusted reference data rather than instructions. This reduces stored prompt-injection risk, but users and agents should still inspect surprising source content before acting on it.

Automatic recall uses a smaller budget than an explicit search and never requests full documents. Change `startup_token_budget`, `prompt_token_budget`, and `capture_max_chars` in `config.ini` when needed. See the [security model](security-model.md) and [architecture](architecture.md) for the complete trust boundary.
