# Release Checklist

Use this checklist before tagging or publishing a context-eval release.

## Local Verification

Run the same quality gates expected in CI:

```bash
python -m pytest
context-eval validate-config --config examples/basic/context-eval.yaml
powershell -ExecutionPolicy Bypass -File scripts\validate-skills.ps1 -SkipExternal
python scripts/check-release-state.py
python -m build --outdir C:\tmp\context-eval-dist
python scripts/inspect-package-artifacts.py C:\tmp\context-eval-dist
python scripts/install-smoke-artifacts.py --dist-dir C:\tmp\context-eval-dist
git diff --check
```

Run `ruff check .` when the dev dependencies are installed.

## Automated Preparation Command

The release preparation entrypoint is:

```bash
python scripts/prepare-release.py --dist-dir C:\tmp\context-eval-dist
```

This command checks CHANGELOG.md, runs the release-state check before package builds, builds wheel and sdist artifacts, inspects artifacts before publish, and runs the release candidate install smoke.
It is a preparation gate only. It does not create Git tags, and it does not upload or publish packages.

The manual publish checkpoint remains after this command succeeds: confirm the
reviewed commit, confirm CI, create the Git tag intentionally, and publish the
already inspected artifacts with the selected package index tooling.

## Release Candidate Install Smoke

Run the install smoke after package artifact inspection:

```bash
python scripts/install-smoke-artifacts.py --dist-dir C:\tmp\context-eval-dist
```

The smoke installs the built wheel into a temporary Python environment, then
runs the installed `context-eval` console script against a local fixture repository,
a fake local agent, temporary local config files, and local run
artifacts. It runs `validate-config`, `run`, `report`, CSV/JSON `export`, and
`ui`, then verifies the generated artifacts are parseable and self-contained.
It also runs the installed `context-eval-app` launcher startup preflight:

```bash
context-eval-app --workspace <temp> --config <temp>/context-eval.yaml --no-browser --port 0 --check-startup
```

That preflight verifies the installed launcher entry point, workspace/config
resolution, loopback startup settings, and local launcher log path without
opening a browser or blocking in the server loop.

The smoke does not call hosted services, does not install or run a real external
coding agent, does not create Git tags, and does not upload or publish packages.
It is still a release candidate gate only; the publish boundary remains a
manual checkpoint.

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

- Run `python scripts/check-release-state.py` before building; it checks hidden local release blockers that `git status --short` does not show.
- The release-state check rejects `.context-eval/`.
- The release-state check rejects `build/`.
- The release-state check rejects `dist/`.
- The release-state check rejects `*.egg-info/`.
- The release-state check rejects `.codex/config.toml`.
- The release-state check allows `.venv/`.
- The release-state check allows cache directories.
- The release-state check allows Ralph local state.
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
6. Build, inspect, and install-smoke artifacts before publishing.
