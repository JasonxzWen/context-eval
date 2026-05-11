# Configuration

The main YAML config defines the target repo, agent adapter, variants, and
optional default validation commands.

```yaml
repo:
  path: "../game-server"
  base_ref: "main"

agent:
  name: "myAgent"
  command: "myAgent -p {prompt_file}"
  timeout_minutes: 60
  network: "disabled"

tasks: "./tasks.yaml"

variants:
  baseline:
    description: "Original AGENTS.md"
    overlays:
      - source: "./contexts/baseline/AGENTS.md"
        target: "AGENTS.md"

evaluation:
  timeout_seconds: 300
  commands:
    - "python -m pytest"
```

Relative paths are resolved from the config file directory, except the default
run output directory, which is `.context-eval/runs` under the current working
directory.

`network` is recorded in results. The MVP does not implement network isolation.

## Agent Telemetry

Agent telemetry is optional. Existing configs use the no-op collector by
default and record `telemetry_status="unavailable"` with
`telemetry_source="none"`.

To collect metrics from a local JSON file written by the agent command, enable
the JSON file collector:

```yaml
agent:
  name: "myAgent"
  command: "myAgent -p {prompt_file} --telemetry {telemetry_file}"
  telemetry:
    collector: "json-file"
    file: "telemetry.json"
```

The `{telemetry_file}` variable is an absolute path for the current case under
the run artifact directory. context-eval also sets
`CONTEXT_EVAL_TELEMETRY_FILE` to that path unless
`environment_variable: null` is configured. The JSON file may include
`prompt_tokens`, `completion_tokens`, `total_tokens`, `reasoning_tokens`,
`tool_call_count`, and `tool_calls_by_name`.

## Validation

Use `context-eval validate-config --config path/to/context-eval.yaml` to parse
the config and task files, resolve local paths, and confirm referenced overlay
sources exist. This default validation does not run an agent, run validation
commands, create workspaces, or require the target repo path to be a Git
repository.

Use `context-eval validate-config --strict --config path/to/context-eval.yaml`
for stronger local preflight checks before running an evaluation. Strict
validation still has no side effects and does not create a workspace. It adds:

- `repo.path` must be a Git repository.
- `repo.base_ref` must resolve in that repository.
- every task-level `repo_ref` must resolve in that repository.

Strict validation is intended to catch local setup errors early. It does not
install dependencies, test target repository commands, check network access, or
validate remote repository state.

### Validation Command Timeouts

`evaluation.timeout_seconds` is an optional default timeout for validation
commands. `task.validation.timeout_seconds` is an optional task-level override
for task-specific validation commands, so task-level timeout overrides the
config-level default. Both fields must be a positive integer number of seconds
when present.

Validation command timeout resolution is independent of command selection:

1. `task.validation.commands` overrides `evaluation.commands`.
2. `task.validation.timeout_seconds` overrides the config-level default.
3. `evaluation.timeout_seconds` applies when no task-level timeout is set.
4. If neither field is set, validation commands run without a timeout.

Example task-level override:

```yaml
tasks:
  - id: "focused-test"
    prompt: "Fix the failing parser test."
    validation:
      timeout_seconds: 60
      commands:
        - "python -m pytest tests/test_parser.py"
```

## Maintainer Tooling

Project-local skills and agent role configs from `skill-hub` are vendored for
maintainers, but active Codex configuration is opt-in. Copy
`.codex/config.example.toml` to `.codex/config.toml` locally only when you want
to enable those workflows.
