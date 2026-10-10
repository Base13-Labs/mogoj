# Mogoj v0.1.0-beta.1

This first public beta makes local, portable AI memory usable from one CLI and installable as Claude Code and Codex/ChatGPT plugins. Markdown remains the source of truth; local SQLite FTS5 provides bounded, cited recall without embeddings or a hosted service.

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/Base13-Labs/mogoj/main/install.sh | sh
~/.local/bin/mogoj onboard
```

Existing users should run `mogoj migrate --dry-run`, then `mogoj migrate`. A timestamped backup is created first. Use `mogoj rollback` to restore generated state; Markdown is never deleted automatically.

## Supported environments

Python 3.9–3.13 on macOS 13+, Ubuntu 22.04/24.04, Windows 11 with PowerShell 7, and Windows 10/11 via WSL2. SQLite 3.35+ with FTS5 is required for recall. Claude Code 1.x and current stable Codex builds are optional integrations.

## Known limitations

- Native Windows has a PowerShell launcher but no one-command installer.
- Token estimates use characters divided by four rather than provider tokenizers.
- BM25 is lexical; rephrase a query when terminology differs.
- No sync, encryption layer, GUI, hosted backup, or recovery service is included.
- Codex distribution is repo-local pending public-directory review.
- Public announcement requires three documented novice-user installation sign-offs.

Report bugs through the [issue forms](https://github.com/Base13-Labs/mogoj/issues/new/choose). Report vulnerabilities privately through [GitHub Security Advisories](https://github.com/Base13-Labs/mogoj/security/advisories/new).
