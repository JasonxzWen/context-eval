# Demo Workflow

[Back to documentation index](index.md).

This workflow exercises context-eval with the bundled fixture repository and
fake local agent. It is deterministic enough for onboarding and does not require
real external coding agents, hosted services, provider credentials, or network
access.

The fixture agent is `examples/fixture-repo/scripts/example_agent.py`. It reads
the rendered prompt file and applies a small local code change that the fixture
tests validate.

## 1. Install Editable Mode

From the repository root:

```bash
python -m pip install -e ".[dev]"
```

## 2. Initialize The Fixture Repository

```bash
python examples/fixture-repo/setup_fixture_repo.py
```

The setup script initializes `examples/fixture-repo` as a local Git repository
on `main` if it has not already been initialized.

## 3. Validate The Example Config

```bash
context-eval validate-config --config examples/basic/context-eval.yaml
```

Use strict validation when you want local Git refs and filename-safe task IDs
checked before a run:

```bash
context-eval validate-config --strict --config examples/basic/context-eval.yaml
```

These checks do not run the fake agent, run validation commands, install
dependencies, or create run workspaces.

## 4. Preview The Matrix

```bash
context-eval run --config examples/basic/context-eval.yaml --dry-run
```

The dry run shows the planned task x variant matrix without creating run
artifacts.

## 5. Run A Small Evaluation

```bash
context-eval run --config examples/basic/context-eval.yaml
```

The example config compares the baseline and experiment context overlays
against one fixture task. The command prints the created run directory under
`.context-eval/runs/<run-id>`.

Generated run directories, exports, static UI files, retained workspaces, and
logs stay under local `.context-eval/` paths in this demo. They are learning
artifacts and should not be committed to the repository.

## 6. Inspect The Run

Replace `<run-id>` with the directory printed by the run command:

```bash
context-eval inspect-run .context-eval/runs/<run-id>
context-eval compare .context-eval/runs/<run-id>
```

Start with `compare` for variant-level observations and risk signals, then open
case artifacts when validation or patch details need review.

## 7. Export CSV And Compact JSON

```bash
context-eval export .context-eval/runs/<run-id> --format csv --output .context-eval/demo-summary.csv
context-eval export .context-eval/runs/<run-id> --format json --output .context-eval/demo-summary.json
```

Exports are derived from local run artifacts. Missing telemetry remains empty in
CSV and `null` in compact JSON.

## 8. Generate The Static UI

```bash
context-eval ui --config examples/basic/context-eval.yaml --run-dir .context-eval/runs/<run-id> --output .context-eval/demo-ui.html
```

The static UI is a self-contained HTML export. It can inspect config and run
artifacts, but it does not save files, run validation commands, or start agents.

## 9. Optional Local App Mode

Use the loopback local app only when you explicitly want browser-based save,
preflight, run, log, result, and export workflows:

```bash
context-eval app --workspace . --config examples/basic/context-eval.yaml
```

The local app is separate from the static UI. It runs on loopback, uses local
files and artifacts, and still does not install coding agents or target
repository dependencies.

## Reading The Demo Results

The fixture output is useful for learning the artifact shape. It is not a
benchmark result. The observations apply only to the fixture repository, the
fixture task, the local fake agent command, the selected variants, and the
validation command in the example config.
