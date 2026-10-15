# Automatic memory in Codex

Mogoj ships as a self-contained Codex desktop plugin: portable metadata, four focused skills, lifecycle hooks, the standard-library Python engine, and a public GitHub marketplace catalog. It has no remote MCP server, account, API key, embedding service, or separate CLI dependency.

## Install

```bash
codex plugin marketplace add Base13-Labs/mogoj --ref main
codex plugin add mogoj@base13-labs
```

Start a new task after installation. Codex will ask you to review and trust the plugin's lifecycle hooks; automatic memory remains disabled until you approve the current hook definition. No Mogoj configuration prompt appears. On the first trusted `SessionStart`, Mogoj creates `~/.mogoj`, builds the local index, and defaults to `auto` mode.

To install a checked-out development copy instead, use:

```bash
codex plugin marketplace add /absolute/path/to/mogoj
codex plugin add mogoj@base13-labs
```

## What happens automatically

- `SessionStart` initializes and synchronizes the local store, then supplies only small current-project context.
- `UserPromptSubmit` searches locally and supplies a bounded, source-cited packet only when useful matches exist.
- `Stop`, `PreCompact`, and `SessionEnd` save conservative, capped, redacted, deduplicated Markdown checkpoints for durable outcomes.

The package contains the engine it invokes. Users do not need to install or place `mogoj` on `PATH`. All automatic behavior fails open so a memory failure cannot prevent Codex from continuing.

Lifecycle:

```bash
codex plugin add mogoj@base13-labs       # install or upgrade
codex plugin remove mogoj@base13-labs
```

Start a new task after install or upgrade so Codex reloads the plugin. Use Settings → Plugins in the desktop app to enable or disable it; the current CLI exposes add, list, marketplace, and remove commands. Disabling or removing the plugin leaves `~/.mogoj` intact.

## Configuration

Defaults are `auto` mode, `~/.mogoj`, approximately 250 estimated startup tokens, and approximately 500 estimated tokens for matching prompt recall. Change these later in `~/.mogoj/config.ini`; supported modes are `auto`, `confirm`, `manual`, and `off`.

## Distribution boundary

The downloadable desktop package is built with:

```bash
python3 scripts/build_codex_plugin.py
```

It produces `dist/mogoj-codex-<version>.zip` plus a SHA-256 checksum. The archive is deterministic and contains only the self-contained plugin.

OpenAI currently limits lifecycle hooks to manually installed Codex desktop plugins and excludes hook-bearing packages from the universal public plugin directory. Publishing a skills-only directory version would remove the feature that makes Mogoj automatic, so Base13 distributes the complete automatic package through its public GitHub marketplace. The relevant OpenAI trust warning is intentional: users should review executable hooks before enabling them.
