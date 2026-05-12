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
- `{telemetry_file}` when the JSON file telemetry collector is enabled

The command runs with the prepared workspace as the current working directory.
The agent may modify files and run commands, but context-eval never commits
changes automatically.

## Planned Agent Profiles

The next adapter expansion is named local agent profiles, specified in
`docs/agent-profiles.md`. Profiles keep the command-template adapter as the
baseline while making Codex CLI, Claude Code, and custom commands such as
`coco -p {prompt_file}` first-class noninteractive configurations.

Existing configs with a single `agent` mapping remain the compatibility shape.
The planned `agents` map is for multi-agent matrices and should not install or
manage coding agents automatically.

## Prompt Templates

Command-template agents may set `prompt_template` to a local file path:

```yaml
agent:
  name: "myAgent"
  command: "myAgent -p {prompt_file}"
  prompt_template: "./prompts/agent-task.md"
```

The `prompt_template` path is resolved relative to the config file. When it is
absent, the built-in prompt remains unchanged.

Prompt templates support these variables:

- `{task_id}`
- `{task_title}`
- `{task_prompt}`
- `{variant}`
- `{repo_ref}`
- `{category}`
- `{difficulty}`

A missing prompt template file fails config validation. An unknown template variable fails
before the agent command runs, so a bad prompt file cannot start an agent with
incomplete instructions.

## Telemetry Collector Lifecycle

Every adapter owns a telemetry collector at the adapter boundary. The
command-template adapter uses `NoOpTelemetryCollector` by default, so existing
configs keep recording `telemetry_status="unavailable"` and
`telemetry_source="none"` unless another collector is configured.

The command-template adapter also supports `JsonFileTelemetryCollector`. When
enabled, it prepares a case-local telemetry file under the case artifact
directory, exposes that absolute path as `{telemetry_file}`, and sets
`CONTEXT_EVAL_TELEMETRY_FILE` to the same path by default. Agent commands can
write JSON like:

```json
{
  "agent_duration_seconds": 12.5,
  "prompt_tokens": 100,
  "completion_tokens": 25,
  "total_tokens": 125,
  "reasoning_tokens": 10,
  "tool_calls_by_name": {
    "read": 2,
    "shell": 1
  }
}
```

`tool_call_count` may be supplied directly. If it is omitted and
`tool_calls_by_name` is present, context-eval derives the total from the
per-tool counts.

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
