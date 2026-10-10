# Mogoj v0.1.0-beta.1

This first public beta gives Claude Code automatic local memory after one plugin install. It recalls small, relevant, source-cited context for each prompt and selectively checkpoints meaningful completed work without requiring the user to run Mogoj commands. Markdown remains the source of truth; local SQLite FTS5 provides bounded recall without embeddings or a hosted service. An optional CLI supports other agents and advanced workflows.

## Install

```bash
claude plugin marketplace add Base13-Labs/mogoj
claude plugin install mogoj@base13-labs
```

Start a new Claude Code session and work normally. The first session creates the private `~/.mogoj` store and local index automatically. The optional standalone CLI is documented in `docs/installation.md`.

There is no Mogoj setup prompt during installation. The plugin starts in `auto` mode. To change recall or saving behavior later, edit `~/.mogoj/config.ini` and choose `auto`, `confirm`, `manual`, or `off` under `[automation]`.

Existing standalone CLI users should run `mogoj migrate --dry-run`, then `mogoj migrate`. A timestamped backup is created first. Use `mogoj rollback` to restore generated state; Markdown is never deleted automatically.

## Supported environments

Python 3.9–3.13 on macOS 13+, Ubuntu 22.04/24.04, Windows 11 with PowerShell 7, and Windows 10/11 via WSL2. SQLite 3.35+ with FTS5 is required for recall. Claude Code 1.x and current stable Codex builds are optional integrations.

## Known limitations

- Native Windows has a PowerShell launcher but no one-command installer.
- Automatic capture is heuristic; explicitly save critical decisions when exact wording matters.
- Token estimates use characters divided by four rather than provider tokenizers.
- BM25 is lexical; rephrase a query when terminology differs.
- No sync, encryption layer, GUI, hosted backup, or recovery service is included.
- Codex distribution is repo-local pending public-directory review.
- Public announcement requires three documented novice-user installation sign-offs.

Report bugs through the [issue forms](https://github.com/Base13-Labs/mogoj/issues/new/choose). Report vulnerabilities privately through [GitHub Security Advisories](https://github.com/Base13-Labs/mogoj/security/advisories/new).
