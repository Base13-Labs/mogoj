# Supported environments

The `0.1.0-beta.1` support contract is intentionally small and testable.

| Component | Supported | Notes |
|---|---|---|
| macOS | 13+ on Intel and Apple Silicon | Python installed separately or by a package manager |
| Linux | Ubuntu 22.04 and 24.04; comparable modern distributions | `python3` must include SQLite FTS5 |
| Windows | Windows 11 with PowerShell 7; Windows 10/11 through WSL2 | Use `mogoj.ps1` natively; symlink creation may require Developer Mode |
| Python | 3.9 through 3.13 | CPython; runtime dependencies are standard-library-only |
| SQLite | 3.35+ with FTS5 enabled | `mogoj doctor` performs a real FTS5 table check |
| Claude Code | 1.x stable channel | Optional; core CLI works without Claude |
| Codex | Current stable desktop app/CLI with Agent Plugins and lifecycle hooks | Automatic local memory after marketplace install and explicit hook trust |

GitHub Actions exercises Python 3.9–3.13 and end-to-end flows on current macOS, Ubuntu, and Windows runners. Paths containing spaces and Unicode are tested everywhere; native Windows runs inherently exercise drive-letter paths. Symlink behavior is tested where the runner permits symlink creation.

The supported flow is install, `init`, `save`, `rebuild`, `search`, `doctor`, migration/upgrade, and uninstall. Python below 3.9 exits with an actionable message. Missing FTS5 is reported by `doctor`; search/rebuild cannot operate until a Python build with FTS5 is installed. Claude and Codex are integrations, not runtime dependencies. Codex web installs cannot run local hooks; automatic behavior requires Codex desktop.
