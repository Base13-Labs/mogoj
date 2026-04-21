# Mogoj — CLAUDE.md

Portable memory system for AI agents. Powered by **Mogoj** (মগজ — Bengali for "brain").

## Purpose

- Give any AI agent persistent, cross-session memory
- Keyword-indexed retrieval with relationship graphs
- Works with Claude Code, Codex, ChatGPT, or any LLM tool
- Zero dependencies — Python 3 stdlib only

## Memory Store Location

The memory store (where your data lives) is at `$MOGOJ_ROOT`. If unset, defaults to `~/code/brain`.

Skills and tools auto-detect: `$MOGOJ_ROOT` → `~/code/brain` → walk up from cwd.

## Directory Structure

```
mogoj/                    # THIS REPO — the engine (portable, shareable)
├── skills/               # Slash commands (symlinked to ~/.claude/commands/)
├── tools/                # Python CLI tools
├── template/             # Empty structure for new memory stores
└── install.sh            # Installer

$MOGOJ_ROOT/              # YOUR DATA — the memory store (private)
├── data/
│   ├── index/            # context-index.json + .md
│   ├── ram/              # current.md + archive/
│   └── sessions/         # saved session docs
├── docs/
│   ├── company/
│   ├── projects/
│   ├── decisions/
│   └── people/
└── imports/
```

## Agent Rules

1. **Read before write.** Always check existing docs before creating new ones.
2. **One file per project** in `docs/projects/`. File name = project slug.
3. **One file per person** in `docs/people/`. File name = first name or nickname.
4. **Don't duplicate.** Update existing entries, don't create parallel docs.
5. **Date everything.** ISO dates (YYYY-MM-DD). Convert relative to absolute.
6. **Mark uncertainty.** Use `[Uncertain]` or `[Inferred]` tags for derived info.
7. **Keep it operational.** Decisions, status, blockers, next steps — not narrative.
8. **Persist meaningful chats.** Use `/mogoj-save` when conversation changes state.

## Topic Routing

| Topic | Route to | Format |
|-------|----------|--------|
| People | `docs/people/{name}.md` | Character profile |
| Projects | `docs/projects/{slug}.md` | Project brief |
| Decisions | `docs/decisions/{date}-{slug}.md` | Decision log |
| Company/Strategy | `docs/company/` | Strategy docs |

## Mogoj Memory System

### Context Index (`data/index/context-index.md`)
- Dictionary-style keyword → doc mapping
- Multiple keywords per doc, multiple docs per keyword
- Alphabetically organized, append-only (mark `[killed]`/`[archived]`, never delete)
- Updated on every `/mogoj-save`
- JSON mirror at `data/index/context-index.json` for Python tools

### RAM (`data/ram/current.md`)
- Live working memory for current/last session
- Overwritten each session (not appended)
- Two tiers: **Hot** (direct refs) and **Warm** (second-degree)
- Multiple concurrent sessions use `data/ram/{session-slug}.md`

### How agents should use it
1. New session starts → read `data/ram/current.md` for last session state
2. Topic comes up → search `data/index/context-index.md` for keyword → read hot refs
3. Need more depth → follow warm refs (two hops max)
4. Session ends (`/mogoj-save`) → write session doc → update index → refresh RAM

## Python Tools

```bash
python3 tools/index.py query <keyword>     # look up keyword
python3 tools/index.py add <keyword> <doc>  # add mapping
python3 tools/index.py build --sync         # rebuild from docs
python3 tools/search.py <query>             # full-text search
python3 tools/graph.py neighbors <doc>      # find related docs
python3 tools/ram.py status                 # check RAM state
python3 tools/ingest.py scan <dir>          # scan external markdown
```

All scripts use stdlib only, no pip install needed.

## Skills

| Skill | What it does |
|-------|-------------|
| `/mogoj-save` | Persist session → index → RAM |
| `/mogoj-search` | Search memory (keyword, full-text, recent) |
| `/mogoj-show` | List all commands + memory stats |
| `/mogoj-debate` | Multi-AI structured debate |
| `/mogoj-plan` | Generate task list for `/run-tasks` |
| `/run-tasks` | Autonomous task executor |

## Multi-Agent Notes

This system is designed for multiple agents. When writing:
- Use atomic, self-contained files
- Avoid cross-references that break if a file is renamed
- Prefer append-friendly formats (lists, sections) over prose
- Assume the next agent may know nothing except what is written here
