# Privacy, security, and data safety

Mogoj is local-first. It has no telemetry, hosted account, analytics beacon, embedding API, or automatic cloud sync. The CLI reads and writes only the memory store you explicitly select; SQLite and indexes live inside that store.

## Data model and boundaries

- Markdown under `docs/`, `data/sessions/`, and `data/ram/` is the source of truth.
- SQLite stores searchable copies of that Markdown plus titles, dates, types, paths, keywords, and access metadata.
- Backups may contain the complete store, including private Markdown. Backup files are mode `0600` by default.
- CLI output contains requested snippets and source citations. Secret warnings name only the matched pattern, never the matched value.
- In Claude Code `auto` mode, the current prompt is used transiently for local retrieval. Meaningful completed turns save a capped checkpoint containing the user request and Claude's final handoff, not the raw transcript. Common secret patterns are redacted before the checkpoint is written.
- `.mogoj/automation-state.json` stores deduplication hashes and the latest checkpoint path; it does not store prompts or responses.
- Mogoj itself makes no network requests for memory, queries, logs, or usage data. In the Claude plugin, matched memory excerpts are deliberately returned as model context and therefore leave the local Mogoj process through Claude Code under the provider's and organization's data-handling settings. Installation and optional marketplace operations are also network-facing workflows.
- Mogoj never intentionally stores environment variables, shell history, credentials, or files outside an explicit import/save operation.

Read-only commands are `status`, `doctor`, `search`, and `recent`. `save`, automatic Claude checkpoints, `init`, `migrate`, `rebuild`, `backup`, `rollback`, and import operations write within the resolved store. Migration and rebuild create a backup and stage SQLite before atomic replacement. Rollback restores generated artifacts but never deletes or replaces Markdown automatically.

## Threat model

Mogoj protects against selecting an unrelated Git repository, path traversal, symlink overwrite, interrupted database rebuilds, accidental secret pastes, permissive newly-created files, and accidental inclusion of databases/backups/imports in Git. Recalled excerpts are labeled as untrusted data rather than instructions to reduce stored prompt-injection risk. Mogoj cannot protect a store from a compromised OS account, an agent or editor already authorized to read the directory, all possible secret formats, a malicious passage that the model still follows, unsafe `--allow-secrets` use, or a cloud/Git client configured by the user.

Before saving, common private-key and provider-token patterns are blocked. Use `--redact` to replace detected values. `--allow-secrets` is an explicit escape hatch for a secured private store; it is never implied.

## Safe operation

- Keep the store outside public repositories. If you version Markdown, use a private repository and review staged changes before every push.
- The generated `.gitignore` excludes `.env`, backups, SQLite, imports, and logs. It does not ignore `docs/`, because private Git versioning is a supported choice.
- Treat `.mogoj/backups/` as sensitive. Encrypt disks and off-device backups, and test restore procedures.
- Review whether Dropbox, iCloud, Google Drive, enterprise backup tools, or endpoint agents can read the chosen directory.
- Run `mogoj doctor` after moving a store or changing permissions.
- Use `--dry-run` for migration, rebuild, and rollback planning. Mogoj does not automatically delete Markdown.

The runtime is Python standard-library-only. Release automation must pin third-party GitHub Actions by commit, and installers must fetch only from the official Base13 Labs repository over HTTPS. Plugins declare no network dependency for memory operations.
