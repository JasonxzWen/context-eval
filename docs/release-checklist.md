# Release Checklist

Use this checklist before tagging or publishing a context-eval release.

## Local Verification

Run the same quality gates expected in CI:

```bash
python -m pytest
context-eval validate-config --config examples/basic/context-eval.yaml
powershell -ExecutionPolicy Bypass -File scripts\validate-skills.ps1 -SkipExternal
python -m build --outdir C:\tmp\context-eval-dist
python scripts/inspect-package-artifacts.py C:\tmp\context-eval-dist
git diff --check
```

Run `ruff check .` when the dev dependencies are installed.

## Supported Runtime And Platforms

The package supports Python 3.11 or newer through `requires-python = ">=3.11"`.
CI gates Python 3.11 and Python 3.12 on pull requests. CI gates Ubuntu and Windows
for the runtime test matrix. macOS is not a release-blocking CI platform yet.

Vendored skill validation is release-blocking on Windows because it depends on
the PowerShell validation script. Other local development hosts may work when
Python and shell prerequisites are available, but they are not part of the
current release gate.

## Packaging Scope

Inspect package configuration before release:

- Inspect both the wheel and sdist after running the build command.
- Run `python scripts/inspect-package-artifacts.py C:\tmp\context-eval-dist`;
  it inspects both the wheel and sdist artifacts.
- The artifact inspection command requires `context_eval/`.
- The artifact inspection command requires `context_eval/reports/templates/`.
- The artifact inspection command rejects `.context-eval/`.
- The artifact inspection command rejects `.agents/`.
- The artifact inspection command rejects `.codex/skills/`.
- The artifact inspection command rejects `openspec/`.
- The artifact inspection command rejects `scripts/`.
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
