# Codex and ChatGPT plugin

Mogoj uses the current portable Agent Plugins format: a root `plugin.json`, packaged `SKILL.md` capabilities, and a repo-local marketplace catalog. The same package is designed for Codex and supported ChatGPT plugin surfaces; it has no remote MCP server or account requirement.

For local development, add this repository's marketplace and install Mogoj:

```bash
codex plugin marketplace add /path/to/mogoj
codex plugin add mogoj@base13-labs
```

Start a new task after install or upgrade so the skills are reloaded. Configure the store with `mogoj onboard` before saving or recalling memory.

Lifecycle:

```bash
codex plugin add mogoj@base13-labs       # install or upgrade
codex plugin disable mogoj@base13-labs
codex plugin enable mogoj@base13-labs
codex plugin remove mogoj@base13-labs
```

If the installed Codex build exposes plugin management only in the app, use Settings → Plugins with the repository-local marketplace. Disabling or removing the plugin leaves the CLI and memory store intact.

The plugin ships only four narrowly described skills. Search calls the token-budgeted local CLI and returns stable Markdown citations. It has no startup hook, telemetry, remote tool, or automatic full-memory injection.
