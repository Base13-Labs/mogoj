# Mogoj (মগজ)

**Portable memory system for AI agents.** Mogoj gives Claude Code, Codex, and other LLM-powered tools persistent, cross-session memory with keyword indexing, relationship graphs, and session management.

## What It Does

- **Persist conversations** — save session summaries with keyword indexing
- **Search memory** — full-text and keyword-based retrieval across all saved sessions
- **RAM management** — live working memory for current/last session state
- **Doc graph** — find relationships between documents via shared keywords
- **Ingest external knowledge** — scan and import markdown from any source
- **Optional workflows** — debates, planning, and autonomous task execution are separate add-ons

## Quick Start

```bash
# Clone
git clone https://github.com/Base13-Labs/mogoj.git ~/code/mogoj

# Install skills (symlinks to ~/.claude/commands/)
cd ~/code/mogoj && ./install.sh

# Initialize a memory store
mogoj init ~/code/brain
# or set MOGOJ_ROOT manually:
export MOGOJ_ROOT=~/code/brain
```

## Architecture

```
mogoj/                    # This repo — the engine
├── skills/               # Slash commands for Claude Code
│   ├── mogoj-save.md     # /mogoj-save — persist session
│   ├── mogoj-search.md   # /mogoj-search — search memory
│   ├── mogoj-show.md     # /mogoj-show — list commands + stats
├── addons/               # Optional higher-permission workflows
├── tools/                # Python CLI tools (stdlib only)
│   ├── index.py          # Keyword index CRUD
│   ├── search.py         # Full-text search
│   ├── graph.py          # Doc relationship graph
│   ├── ram.py            # RAM lifecycle
│   └── ingest.py         # Import from external sources
├── template/             # Empty directory structure for new stores
└── install.sh            # Symlinks skills to ~/.claude/commands/
```

Your data lives separately (e.g., `~/code/brain/`):

```
brain/                    # Your memory store (private)
├── data/
│   ├── index/            # context-index.json + .md
│   ├── ram/              # current.md + archive/
│   └── sessions/         # saved session docs
├── docs/
│   ├── company/          # company-level context
│   ├── projects/         # per-project briefs
│   ├── decisions/        # decision logs
│   └── people/           # character profiles
└── imports/              # raw exports from external tools
```

## Skills

| Command | What it does |
|---------|-------------|
| `/mogoj-save` | Persist session to memory (index + RAM) |
| `/mogoj-search` | Search across all memory |
| `/mogoj-show` | List all commands + memory stats |
Optional debate, planning, and autonomous execution workflows are not installed
by default. They are not required for memory capture or retrieval.

## Tools

All Python tools use stdlib only — no pip install needed. Python 3.9+.

```bash
python3 tools/index.py build          # Scan docs, build keyword index
python3 tools/index.py query chatx    # Look up a keyword
python3 tools/index.py add sales doc  # Add keyword mapping
python3 tools/search.py "query"       # Full-text search
python3 tools/graph.py build          # Build relationship graph
python3 tools/graph.py neighbors doc  # Find related docs
python3 tools/ram.py status           # Check RAM state
python3 tools/ingest.py scan ~/dir    # Scan external markdown
```

## Configuration

Set `MOGOJ_ROOT` to point at your memory store:

```bash
export MOGOJ_ROOT=~/code/brain
```

If unset, defaults to `~/code/brain`.

## License

MIT
