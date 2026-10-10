# Claude Code plugin

Install the CLI first, then register the Base13 Labs marketplace and install the core plugin:

```bash
claude plugin marketplace add Base13-Labs/mogoj
claude plugin install mogoj@base13-labs
```

Start a new Claude Code session, then ask it to save a memory or recall a prior decision. The plugin delegates deterministic storage and bounded retrieval to the same `mogoj` CLI used everywhere else.

Lifecycle commands:

```bash
claude plugin update mogoj@base13-labs
claude plugin disable mogoj@base13-labs
claude plugin enable mogoj@base13-labs
claude plugin uninstall mogoj@base13-labs
```

Plugin removal never removes the CLI or memory store. Install optional workflows separately with `claude plugin install mogoj-workflows@base13-labs`.

The core plugin has four short skill descriptions in baseline context. Full instructions load only when invoked. It defines no hook, MCP server, monitor, or automatic session-start memory injection, so it cannot inject unbounded memories. Search uses Mogoj's default 1,200-token retrieval budget.
