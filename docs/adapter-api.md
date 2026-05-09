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

## Telemetry Collector Lifecycle

Every adapter owns a telemetry collector at the adapter boundary. The
command-template adapter uses `NoOpTelemetryCollector` by default, so existing
configs keep recording `telemetry_status="unavailable"` and
`telemetry_source="none"` unless a future collector is configured.

Collectors have two local-only hooks:

1. `prepare(...)` runs before the command starts and may return additional
   command template variables or environment variables for the current case.
2. `collect(...)` runs after the command exits and returns a
   `TelemetryCollectionResult` with normalized status, source, error, token
   counts, and tool-call counts.

Collectors must observe local artifacts only. They must not call hosted APIs,
upload logs, estimate billing through a remote service, or execute an agent
command themselves. A collector failure is reported as telemetry error state; it
must not reinterpret the agent's exit code or validation result.
