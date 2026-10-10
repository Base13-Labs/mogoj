# Privacy, security, and data safety

Mogoj is local-first. It has no telemetry, hosted account, analytics beacon, embedding API, or automatic cloud sync. The CLI reads and writes only the memory store you explicitly select; SQLite and indexes live inside that store.

## Data model and boundaries

- Markdown under `docs/`, `data/sessions/`, and `data/ram/` is the source of truth.
- SQLite stores searchable copies of that Markdown plus titles, dates, types, paths, keywords, and access metadata.
- Backups may contain the complete store, including private Markdown. Backup files are mode `0600` by default.
- CLI output contains requested snippets and source citations. Secret warnings name only the matched pattern, never the matched value.
- Mogoj never sends memory, queries, logs, or usage data over the network. Installation and optional marketplace operations are the only network-facing workflows.
- Mogoj never intentionally stores environment variables, shell history, credentials, or files outside an explicit import/save operation.

Read-only commands are `status`, `doctor`, `search`, and `recent`. `save`, `init`, `migrate`, `rebuild`, `backup`, `rollback`, and import operations write within the resolved store. Migration and rebuild create a backup and stage SQLite before atomic replacement. Rollback restores generated artifacts but never deletes or replaces Markdown automatically.

## Threat model

Mogoj protects against selecting an unrelated Git repository, path traversal, symlink overwrite, interrupted database rebuilds, accidental secret pastes, permissive newly-created files, and accidental inclusion of databases/backups/imports in Git. It cannot protect a store from a compromised OS account, an agent or editor already authorized to read the directory, unsafe `--allow-secrets` use, or a cloud/Git client configured by the user.

Before saving, common private-key and provider-token patterns are blocked. Use `--redact` to replace detected values. `--allow-secrets` is an explicit escape hatch for a secured private store; it is never implied.

## Safe operation

- Keep the store outside public repositories. If you version Markdown, use a private repository and review staged changes before every push.
- The generated `.gitignore` excludes `.env`, backups, SQLite, imports, and logs. It does not ignore `docs/`, because private Git versioning is a supported choice.
- Treat `.mogoj/backups/` as sensitive. Encrypt disks and off-device backups, and test restore procedures.
- Review whether Dropbox, iCloud, Google Drive, enterprise backup tools, or endpoint agents can read the chosen directory.
- Run `mogoj doctor` after moving a store or changing permissions.
- Use `--dry-run` for migration, rebuild, and rollback planning. Mogoj does not automatically delete Markdown.

The runtime is Python standard-library-only. Release automation must pin third-party GitHub Actions by commit, and installers must fetch only from the official Base13 Labs repository over HTTPS. Plugins declare no network dependency for memory operations.
