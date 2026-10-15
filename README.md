# Mogoj

Mogoj gives Claude Code and Codex private, automatic, durable memory on your machine—and recalls only the useful, source-cited context that fits your token budget. A CLI remains available for other agents and advanced use, but normal plugin use requires no Mogoj commands.

> **Beta:** `v0.1.0-beta.1` is for early adopters. Back up important stores, review retrieved context before relying on it, and report bugs with synthetic data.

![A terminal installs Mogoj, saves a decision, and recalls it](docs/assets/terminal-demo.gif)

## Automatic Claude Code memory in about 60 seconds

Install the Base13 marketplace and plugin once:

```bash
claude plugin marketplace add Base13-Labs/mogoj
claude plugin install mogoj@base13-labs
```

Then use Claude Code normally. Installation asks for no Mogoj configuration: on the next session Mogoj defaults to `auto`, creates a private `~/.mogoj` store, builds the local index, recalls relevant context for each prompt, and checkpoints meaningful completed work. You do not have to run `mogoj`, ask Claude to remember, or paste previous-session context.

To change the behavior later, edit `~/.mogoj/config.ini` and set `mode` under `[automation]` to `confirm`, `manual`, or `off`. The same file controls startup/prompt budgets and maximum checkpoint size.

Example: in one session, tell Claude:

```text
Use SQLite for local search and add the migration tests.
```

Open a new Claude Code session later and ask, “Why did we choose SQLite?” Mogoj automatically places the relevant bounded checkpoint beside that prompt, with a source citation such as `data/sessions/2026-10-10-claude-my-project-a1b2c3d4.md:L1-L12`. Claude sees continuity without receiving the whole memory store.

For terminal-only or non-Claude use, see the optional [CLI installation guide](docs/installation.md).

## Automatic Codex memory

Add the public Base13 Labs marketplace and install Mogoj:

```bash
codex plugin marketplace add Base13-Labs/mogoj --ref main
codex plugin add mogoj@base13-labs
```

Start a new Codex task, review and trust the packaged lifecycle hooks when prompted, and work normally. The Codex package contains its own Mogoj runtime, defaults to `auto`, and uses the same private `~/.mogoj` store as Claude Code. See the [Codex plugin guide](docs/codex-plugin.md) for lifecycle and security details.

The optional CLI remains fully supported for scripting, other agents, and explicit control:

```bash
mogoj onboard
mogoj save "Use SQLite for local search" --title "Database decision" --type decision
mogoj rebuild
mogoj search "Why SQLite?"
mogoj migrate --dry-run
mogoj doctor
mogoj rollback --dry-run
```

## Your data stays understandable

Markdown is the source of truth. The local SQLite FTS5 database is a disposable search accelerator. Mogoj has no telemetry, cloud account, embedding API, or independent network upload. New files and backups are private by default; common secret patterns are blocked before save. In automatic mode, matched excerpts are deliberately added to Claude's model context and are therefore governed by your Claude Code provider and organization data settings.

```text
~/.mogoj/                  your private store
├── .mogoj/                marker, migration state, backups
├── docs/                  durable Markdown memories
├── data/sessions/         session handoffs
├── data/ram/              small active-memory pointers
└── data/db/mogoj.db       rebuildable local search index
```

Read the [privacy and threat model](docs/security-model.md) before putting a store in Git or a cloud-synced folder.

## Supported agents

- Claude Code: install the [automatic-memory plugin](docs/claude-plugin.md); normal use is zero-command.
- CLI: an optional deterministic interface for any assistant, editor, or advanced workflow.
- Codex desktop: install the [automatic-memory plugin](docs/codex-plugin.md); normal use is zero-command after hook trust.
- Optional debate/planning/task-running workflows are a separate add-on; they do not ship in the memory core.

See the [platform matrix](docs/platform-support.md) for tested operating systems, Python, SQLite, and integration versions.

## How recall works

Mogoj indexes Markdown locally with SQLite FTS5/BM25. In Claude Code, a `UserPromptSubmit` hook turns the current prompt and project into a focused local query. Retrieval is progressive: a compact result index, one ranked snippet per document, then full content only when explicitly requested and still within budget. Automatic prompt recall defaults to about 500 estimated tokens; explicit CLI search defaults to about 1,200.

At `Stop`, `PreCompact`, and `SessionEnd`, Mogoj selectively checkpoints durable outcomes such as implemented changes, decisions, test results, blockers, and next steps. It ignores short conversational noise, redacts common secret patterns, caps saved text, and deduplicates repeated lifecycle events. It stores a structured handoff rather than a raw transcript.

Mogoj is not a generic vector database. It does not require embeddings, a model call, a server, chunk hosting, or opaque binary source data. Choose a vector database when you need semantic retrieval over very large corpora or a multi-user service. Choose Mogoj when humans should own readable files, citations and migrations matter, and the context window—not storage—is the scarce resource. See the [published beta benchmark](docs/beta-retrieval-benchmark.md).

## Architecture in 30 seconds

Mogoj separates the **engine** from the **memory store**. The engine is the deterministic local runtime and agent plugins in this repository. The store is a private directory owned by the user. Markdown in that store is canonical; SQLite FTS5 is a disposable, rebuildable index. Claude lifecycle hooks call the same engine used by the optional CLI, so automatic and manual operation share storage, privacy checks, retrieval budgets, and citations.

```text
agent lifecycle hooks ───┐
agent skill/plugin ──────┤
                         ▼
optional terminal ──► Mogoj engine
                        │
             ┌──────────┴──────────┐
             ▼                     ▼
    Markdown source of truth   SQLite FTS5 index
    decisions, projects,       derived and safe
    sessions, active memory    to delete/rebuild
             │                     │
             └──────────┬──────────┘
                        ▼
              bounded cited context
```

The central design choice is to optimize the *context sent to an AI*, not to maximize stored data. Automatic recall returns a small cited packet only when a prompt has a useful match, and automatic capture stores durable outcomes rather than every turn. Read the [long-form architecture and design reasoning](docs/architecture.md) for component boundaries, hook flows, safety properties, and trade-offs.

## Upgrade, migration, and rollback

Re-run the installer to add a new engine version. Preview store changes before upgrading:

```bash
~/.local/bin/mogoj migrate --dry-run
~/.local/bin/mogoj migrate
~/.local/bin/mogoj doctor
```

Migration creates a timestamped private backup, stages SQLite separately, verifies integrity, and atomically replaces generated state. It never deletes Markdown. To restore generated state from the newest backup:

```bash
~/.local/bin/mogoj rollback
```

## Five common problems

1. **`mogoj: command not found`:** run `~/.local/bin/mogoj doctor`. The installer prints this full path specifically so no profile edit is required.
2. **“No Mogoj store found”:** run `~/.local/bin/mogoj onboard`, or pass `--root "/your/store"` before the command.
3. **Search says the index is missing:** run `~/.local/bin/mogoj rebuild`, then retry.
4. **Doctor reports SQLite FTS5 unavailable:** install a supported Python build with FTS5, then run doctor again. Mogoj cannot emulate full-text search safely.
5. **Save blocks a possible secret:** use `--redact`. Use `--allow-secrets` only after confirming the store and every backup/sync destination are private.

For a corrupted index, run `mogoj rebuild`; for an interrupted migration, rerun it—the stale staging database is removed safely. Installation details and uninstall are in [the installation guide](docs/installation.md).

## Honest beta limitations

- Native Windows has a PowerShell launcher but not yet a one-command installer; WSL is the easiest Windows path.
- Token counts use a deterministic character estimate, not a provider-specific tokenizer.
- Search is lexical BM25, so differently worded concepts may require a second query.
- Automatic capture is heuristic. Review important checkpoints and use explicit save for critical wording.
- No multi-device synchronization, encryption layer, GUI, hosted backup, or recovery service is included.
- Automatic hooks require a manually installed Codex desktop plugin and explicit hook trust. OpenAI's universal public directory does not accept hook-bearing plugins.

## Example and handoff

Explore the fictional, non-sensitive [example store](examples/fictional-store) and the [before/after context handoff](docs/context-handoff-example.md). No Base13 Labs private memory is included.

## Contributing and support

- [Contributing](CONTRIBUTING.md)
- [Support expectations](SUPPORT.md)
- [Private vulnerability reporting](SECURITY.md)
- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Open an issue](https://github.com/Base13-Labs/mogoj/issues/new/choose)

Mogoj (মগজ) means “brain” in Bengali. Copyright 2026 Base13 Labs; released under the [MIT License](LICENSE).
