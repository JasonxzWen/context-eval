# Release Checklist

Use this checklist before tagging or publishing a context-eval release.

## Local Verification

Run the same quality gates expected in CI:

```bash
python -m pytest
context-eval validate-config --config examples/basic/context-eval.yaml
powershell -ExecutionPolicy Bypass -File scripts\validate-skills.ps1 -SkipExternal
git diff --check
```

Run `ruff check .` when the dev dependencies are installed.

## Packaging Scope

Inspect package configuration before release:

- `context_eval` is the runtime package and should be included.
- `context_eval/reports/templates/*.j2` should be included as package data.
- `.agents/`, `.codex/skills/`, `openspec/`, and `scripts/` are maintainer
  capability library files in the repository, not runtime package modules.
- `.context-eval/` run artifacts must not be included.
- Active `.codex/config.toml` must not be committed; use
  `.codex/config.example.toml` only.

## Release Steps

1. Update `CHANGELOG.md`.
2. Confirm the working tree is clean.
3. Run the local verification commands above.
4. Confirm CI passes on the release branch or pull request.
5. Tag the release from the reviewed commit.
6. Build and inspect artifacts once `python -m build` is part of the dev
   dependency set.
