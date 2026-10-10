# Changelog

All notable changes are documented here. Mogoj uses semantic versioning; the single version source is `VERSION`.

## [0.1.0-beta.1] - 2026-10-10

### Added

- Beginner-friendly `mogoj` CLI with onboarding, save, bounded search, doctor, migration, backup, rebuild, rollback, and JSON output.
- Local SQLite FTS5/BM25 retrieval with token budgets, source citations, metadata filters, and no embedding dependency.
- Atomic, backed-up migration from the public v0 template and Base13-style stores.
- Claude Code and Codex/ChatGPT plugin packages with repo-local marketplaces and optional workflows separated from memory core.
- One-command macOS/Linux installer, PowerShell launcher, privacy protections, governance files, cross-platform CI, and release automation.

### Security

- Store markers prevent writes to unrelated repositories.
- Path traversal and symlink overwrite are rejected.
- Common secret patterns are blocked or explicitly redacted before save.
- No telemetry or automatic remote memory transfer.

[0.1.0-beta.1]: https://github.com/Base13-Labs/mogoj/releases/tag/v0.1.0-beta.1
