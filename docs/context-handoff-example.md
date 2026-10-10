# Before and after: context handoff

## Before Mogoj

> “Continue the launch work.”

The assistant has no durable context. The user repeats the launch date, target audience, chosen database, unresolved risks, and links. A common workaround pastes entire transcripts, spending thousands of tokens before useful work starts.

## After Mogoj

The same request triggers a focused search. Mogoj returns a compact index and one passage per distinct source within the configured budget:

```text
[docs/projects/aurora.md:L5-L7]
Launch target: 2026-11-02. Audience: small design agencies.

[docs/decisions/2026-10-01-local-search.md:L1-L4]
Decision: use SQLite FTS5 so source memory stays local and rebuildable.
```

The assistant continues with the decision and open risks, while the user can inspect the exact Markdown lines. Full documents remain on disk until explicitly needed.
