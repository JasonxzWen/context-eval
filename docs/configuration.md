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
