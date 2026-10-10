# Optional workflow add-ons

These workflows are intentionally excluded from the default Mogoj install.
They can modify application repositories, call additional AI tools, or run
tasks autonomously; none is required to save, search, or maintain memory.

- `mogoj-debate.md` — orchestrates multi-model debates.
- `mogoj-plan.md` — writes executable project plans.
- `run-tasks.md` — executes project tasks autonomously.

Legacy installation:

```bash
claude plugin install mogoj-workflows@base13-labs
```

Removing this add-on directory or its command links never removes a Mogoj
memory store.
