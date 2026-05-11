# Release Checklist

Use this checklist before tagging or publishing a context-eval release.

## Local Verification

Run the same quality gates expected in CI:

```bash
python -m pytest
context-eval validate-config --config examples/basic/context-eval.yaml
powershell -ExecutionPolicy Bypass -File scripts\validate-skills.ps1 -SkipExternal
python -m build --outdir C:\tmp\context-eval-dist
git diff --check
```

Run `ruff check .` when the dev dependencies are installed.

## Packaging Scope

Inspect package configuration before release:

- Inspect both the wheel and sdist after running the build command.
- Package metadata must use `project.license` as an SPDX string, currently
  `license = "MIT"`.
- Package metadata must not use table-form license metadata such as
  `license = { text = "MIT" }`.
- The artifacts must include entries that show it includes `context_eval/`.
- The artifacts must include entries that show it includes `context_eval/reports/templates/`.
- The artifacts do not include `.context-eval/`.
- The artifacts do not include `.agents/`.
- The artifacts do not include `.codex/skills/`.
- The artifacts do not include `openspec/`.
- The artifacts do not include `scripts/`.
- License metadata modernization does not change the runtime package scope.
- Active `.codex/config.toml` must not be committed; use
  `.codex/config.example.toml` only.

## Release Steps

1. Update `CHANGELOG.md`.
2. Confirm the working tree is clean.
3. Run the local verification commands above.
4. Confirm CI passes on the release branch or pull request.
5. Tag the release from the reviewed commit.
6. Build and inspect artifacts before publishing.
