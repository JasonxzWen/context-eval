## ADDED Requirements

### Requirement: Read Codex Desktop session JSONL inputs

The system SHALL provide a dedicated read-only diagnostics command for local
Codex Desktop session JSONL files.

#### Scenario: User passes explicit session files

- **WHEN** the user runs the diagnostics command with one or more existing
  `.jsonl` file paths
- **THEN** the system reads those files without modifying them and summarizes
  only the supplied files

#### Scenario: User passes a Windows glob pattern

- **WHEN** the user runs the diagnostics command with a path pattern such as
  `C:\Users\Admin\.codex\sessions\2026\05\27\*.jsonl`
- **THEN** the system expands matching files deterministically and summarizes
  the matched files in path order

#### Scenario: No files match

- **WHEN** no supplied file path or glob pattern resolves to a readable file
- **THEN** the command exits non-zero with a concise error and does not create
  output artifacts

### Requirement: Parse Codex Desktop session events independently

The system SHALL parse Codex Desktop session JSONL as a separate format from
context-eval `results.jsonl` and case-local `codex exec --json` telemetry.

#### Scenario: Known top-level row types are counted

- **WHEN** a session file contains rows with top-level types such as
  `session_meta`, `turn_context`, `event_msg`, and `response_item`
- **THEN** the summary records row counts by top-level type

#### Scenario: Known payload types are counted

- **WHEN** a session file contains payload types such as `token_count`,
  `function_call`, `function_call_output`, `message`, `agent_message`,
  `task_started`, or `task_complete`
- **THEN** the summary records payload counts by payload type without printing
  payload body text

#### Scenario: Unknown fields are tolerated

- **WHEN** a valid JSONL event includes unknown fields or unknown payload types
- **THEN** the parser continues, counts the event, and preserves deterministic
  aggregate unknown-type counts

#### Scenario: Malformed lines are reported

- **WHEN** a session file contains malformed JSON lines
- **THEN** the summary records malformed line counts for that file and continues
  parsing remaining valid lines

### Requirement: Report operational diagnostics

The system SHALL report aggregate operational signals that can help users
understand local Codex session behavior.

#### Scenario: Token observations are present

- **WHEN** session events contain `token_count` payload observations
- **THEN** the summary reports token observation counts plus latest and maximum
  available token fields as local observations

#### Scenario: Tool and function calls are present

- **WHEN** session events contain `function_call`, `custom_tool_call`, or
  related call payloads with names
- **THEN** the summary reports call counts by payload type and by call name

#### Scenario: Tool outputs are present

- **WHEN** session events contain `function_call_output`,
  `custom_tool_call_output`, or related output payloads with status fields
- **THEN** the summary reports output counts by payload type and status without
  printing output content

#### Scenario: Error signals are present

- **WHEN** session events contain failure, error, rollback, or non-success
  status signals
- **THEN** the summary reports those counts and identifies top sessions by
  diagnostic signal count

#### Scenario: Rate-limit observations are present

- **WHEN** session events contain rate-limit metadata
- **THEN** the summary reports the count of rate-limit observations without
  estimating remaining quota or billing cost

### Requirement: Keep default output content-safe

The system MUST NOT include prompt text, assistant message text, reasoning
content, tool arguments, or tool output bodies in default terminal or JSON
output.

#### Scenario: Message payloads are present

- **WHEN** session events contain message-like payloads with content fields
- **THEN** the summary counts the message payloads but omits the content text

#### Scenario: Tool payloads are present

- **WHEN** session events contain tool arguments or tool output bodies
- **THEN** the summary counts names, statuses, and aggregate sizes only and
  omits raw argument and output text

### Requirement: Provide deterministic terminal and JSON summaries

The system SHALL provide both a human-readable terminal summary and a
script-friendly JSON summary.

#### Scenario: Terminal summary is requested by default

- **WHEN** the user runs the diagnostics command without an output format flag
- **THEN** the system prints session count, turn count, row and payload
  counters, token observations, tool-call counters, error counts, rate-limit
  observations, and top sessions by size or diagnostic signal

#### Scenario: JSON summary is requested

- **WHEN** the user runs the diagnostics command with JSON output enabled
- **THEN** the system writes deterministic JSON with sorted files, sorted
  counter keys, explicit `null` values for unavailable scalar observations, and
  no raw payload bodies

### Requirement: Preserve existing context-eval run behavior

The system SHALL leave existing context-eval run inspection and telemetry
collection semantics unchanged.

#### Scenario: Existing run inspection still requires results

- **WHEN** the user runs `inspect-run` on a directory that does not contain
  `results.jsonl`
- **THEN** the command continues to fail with the existing missing-results error
  instead of treating the directory as Codex sessions

#### Scenario: Existing Codex telemetry collector remains case-local

- **WHEN** a context-eval run uses the `codex-jsonl` telemetry collector
- **THEN** it continues to read case-local `codex-events.jsonl` artifacts rather
  than global Codex Desktop session logs
