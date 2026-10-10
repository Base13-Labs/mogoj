# Installation and onboarding

## Primary path

On macOS or Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/Base13-Labs/mogoj/main/install.sh | sh
```

The installer explains its locations before writing, downloads only from the official Base13 Labs GitHub repository over HTTPS, stores versioned engines under `~/.local/share/mogoj`, and places the command at `~/.local/bin/mogoj`. If that directory is not on `PATH`, it prints the full command; no profile edit is required. Onboarding asks for memory location, agents, and an optional Markdown import folder.

This managed shell path was chosen over `uv tool install` and `pipx` because it does not require a beginner to install or understand a Python package manager. A signed standalone binary is a future improvement; the beta remains auditable standard-library Python.

## Offline/contributor fallback

```bash
./install.sh --source . --yes
~/.local/bin/mogoj onboard
```

Windows users can run `pwsh bin/mogoj.ps1 onboard` from a release checkout.

## Upgrade and uninstall

Re-run the installer to install a new version and repoint the command. When release notes require it, run `mogoj migrate --dry-run` and then `mogoj migrate`.

```bash
curl -fsSL https://raw.githubusercontent.com/Base13-Labs/mogoj/main/uninstall.sh | sh
```

Uninstall removes only the engine and command link. It preserves `~/.mogoj`, custom stores, and backups.

The automated suite exercises five clean-machine personas. Three novice human sign-offs must additionally complete `docs/usability-test-script.md` before public announcement; automated tests cannot substitute for that evidence.
