# Adapter API

The MVP includes one adapter: a command template adapter.

```yaml
agent:
  name: "myAgent"
  command: "myAgent -p {prompt_file}"
  timeout_minutes: 60
  network: "disabled"
```

Supported template variables:

- `{workspace}`
- `{prompt}`
- `{prompt_file}`
- `{task_id}`
- `{variant}`
- `{output_dir}`

The command runs with the prepared workspace as the current working directory.
The agent may modify files and run commands, but context-eval never commits
changes automatically.
