# Skill Hub Import

This repository vendors the development capability library from:

- Source: `https://github.com/JasonxzWen/skill-hub`
- Imported commit: `65523f9211a1bf8adaf9247f3dfbc14484251f1e`
- Import date: `2026-05-08`

Imported capability roots:

- `.agents/skills/`
- `.codex/skills/`
- `.codex/agents/`
- `openspec/`
- `scripts/`

The upstream repository's `AGENTS.md` and `README.md` files were intentionally
not imported. Files named `AGENTS.md` or `README*` inside the imported roots
were also skipped to avoid changing this repository's agent instructions or
duplicating upstream project documentation.

The imported assets are used as project-local development support: skill
definitions, focused agent role configs, OpenSpec helpers, Ralph loop scripts,
and validation utilities. They are not part of the `context_eval` runtime
package unless explicitly referenced by future packaging changes.

Most upstream skill-hub documentation was intentionally removed from this
repository because it describes general skill-pack research, source-project
analysis, and local setup workflows that are not specific to context-eval. This
file is the retained provenance record.

The optional Codex configuration is tracked as `.codex/config.example.toml`.
Maintainers can copy it to `.codex/config.toml` locally when they want to opt in
to the project-local skills and agent roles. The active `.codex/config.toml`
path is ignored so ordinary clones do not silently enable external tooling.
