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
  commands:
    - "python -m pytest"
```

Relative paths are resolved from the config file directory, except the default
run output directory, which is `.context-eval/runs` under the current working
directory.

`network` is recorded in results. The MVP does not implement network isolation.

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

## Maintainer Tooling

Project-local skills and agent role configs from `skill-hub` are vendored for
maintainers, but active Codex configuration is opt-in. Copy
`.codex/config.example.toml` to `.codex/config.toml` locally only when you want
to enable those workflows.
