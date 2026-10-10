# Installation and onboarding

## Primary path: automatic Claude Code memory

Install the marketplace and plugin once:

```bash
claude plugin marketplace add Base13-Labs/mogoj
claude plugin install mogoj@base13-labs
```

Start a new Claude Code session and work normally. The plugin contains the Mogoj runtime, initializes `~/.mogoj` on first use, recalls relevant source-cited context automatically, and checkpoints meaningful completed work. No separate Python package, `mogoj` command, onboarding wizard, account, or API key is required.

See [Automatic memory in Claude Code](claude-plugin.md) for modes, budgets, lifecycle behavior, update, disable, and uninstall instructions.

## Optional standalone CLI

On macOS or Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/Base13-Labs/mogoj/main/install.sh | sh
```

The installer explains its locations before writing, downloads only from the official Base13 Labs GitHub repository over HTTPS, stores versioned engines under `~/.local/share/mogoj`, and places the command at `~/.local/bin/mogoj`. If that directory is not on `PATH`, it prints the full command; no profile edit is required. Onboarding asks for memory location, agents, and an optional Markdown import folder.

Use this path for terminal-only operation, non-Claude agents, explicit store management, or contributor diagnostics. It was chosen over `uv tool install` and `pipx` because it does not require a Python package manager. A signed standalone binary is a future improvement; the beta remains auditable standard-library Python.

## Offline/contributor CLI fallback

```bash
./install.sh --source . --yes
~/.local/bin/mogoj onboard
```

Windows users can run `pwsh bin/mogoj.ps1 onboard` from a release checkout.

## CLI upgrade and uninstall

Re-run the installer to install a new version and repoint the command. When release notes require it, run `mogoj migrate --dry-run` and then `mogoj migrate`.

```bash
curl -fsSL https://raw.githubusercontent.com/Base13-Labs/mogoj/main/uninstall.sh | sh
```

Uninstall removes only the engine and command link. It preserves `~/.mogoj`, custom stores, and backups.

The automated suite exercises clean-machine CLI personas and the Claude plugin install/disable/enable/uninstall lifecycle. Three novice human sign-offs must additionally complete `docs/usability-test-script.md` before public announcement; automated tests cannot substitute for that evidence.
