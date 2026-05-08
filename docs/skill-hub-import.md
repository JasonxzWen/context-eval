# Skill Hub Import

This repository vendors the development capability library from:

- Source: `https://github.com/JasonxzWen/skill-hub`
- Imported commit: `65523f9211a1bf8adaf9247f3dfbc14484251f1e`
- Import date: `2026-05-08`

Imported capability roots:

- `.agents/skills/`
- `.codex/skills/`
- `.codex/agents/`
- `docs/`
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
