from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

from context_eval.compare import _variant_stats
from context_eval.config import ConfigError, validate_config_files
from context_eval.config_editor import EditableConfigModel, build_editable_model
from context_eval.export import agent_summary_rows, has_multiple_agents
from context_eval.inspect_run import _load_metadata, _load_results
from context_eval.models import CaseResult, ContextEvalConfig, TaskFile
from context_eval.reporting import (
    format_matrix_overview_inline,
    format_optional_int,
    format_optional_number,
    format_status_counts,
    matrix_cell_rows,
    run_matrix_overview,
)
from context_eval.workspace import slugify


def render_local_ui(
    *,
    config_path: Path | None,
    run_dir: Path | None,
    output_path: Path,
) -> Path:
    if config_path is None and run_dir is None:
        raise ConfigError("context-eval ui requires --config or --run-dir")

    config: ContextEvalConfig | None = None
    tasks: TaskFile | None = None
    results: list[CaseResult] = []
    metadata: dict[str, Any] = {}

    if config_path is not None:
        config, tasks = validate_config_files(config_path)
    if run_dir is not None:
        results = _load_results(run_dir)
        metadata = _load_metadata(run_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        _html(config=config, tasks=tasks, results=results, metadata=metadata),
        encoding="utf-8",
    )
    return output_path


def _html(
    *,
    config: ContextEvalConfig | None,
    tasks: TaskFile | None,
    results: list[CaseResult],
    metadata: dict[str, Any],
) -> str:
    run_id = metadata.get("run_id") or (results[0].run_id if results else "none")
    editor = (
        build_editable_model(config, tasks) if config is not None and tasks is not None else None
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>context-eval local UI</title>
  <style>
    :root {{
      color-scheme: light;
      --paper: #f7f5ef;
      --ink: #1f2520;
      --muted: #657067;
      --line: #cfd5cb;
      --panel: #ffffff;
      --accent: #146c5c;
      --accent-2: #a45322;
      --warn: #9f6b00;
      --ok: #196b38;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--paper);
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
      letter-spacing: 0;
    }}
    main {{
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 28px 0 48px;
    }}
    header {{
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 24px;
      align-items: end;
      border-bottom: 2px solid var(--ink);
      padding-bottom: 18px;
      margin-bottom: 24px;
    }}
    h1, h2 {{
      margin: 0;
      font-weight: 700;
      line-height: 1.05;
    }}
    h1 {{ font-size: 34px; }}
    h2 {{ font-size: 22px; margin-bottom: 12px; }}
    .stamp {{
      border: 1px solid var(--ink);
      padding: 8px 10px;
      text-transform: uppercase;
      font: 700 12px/1.2 Consolas, "Courier New", monospace;
      color: var(--accent);
      background: #eef4ed;
    }}
    section {{
      margin: 26px 0;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }}
    label {{
      display: grid;
      gap: 6px;
      color: var(--muted);
      font: 700 12px/1.2 Consolas, "Courier New", monospace;
      text-transform: uppercase;
    }}
    input, textarea, select {{
      width: 100%;
      min-width: 0;
      border: 1px solid var(--line);
      border-radius: 4px;
      padding: 10px 12px;
      background: var(--panel);
      color: var(--ink);
      font: 14px/1.4 Consolas, "Courier New", monospace;
    }}
    textarea {{ min-height: 92px; resize: vertical; }}
    select {{ appearance: auto; }}
    fieldset {{
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 14px;
      margin: 0 0 14px;
      background: rgba(255, 255, 255, 0.55);
    }}
    legend {{
      color: var(--accent);
      font: 700 12px/1.2 Consolas, "Courier New", monospace;
      text-transform: uppercase;
      padding: 0 6px;
    }}
    .subgrid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-top: 12px;
    }}
    .resolved {{
      margin-top: 10px;
      color: var(--muted);
      font-size: 13px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: var(--panel);
      border: 1px solid var(--line);
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 10px 12px;
      vertical-align: top;
      text-align: left;
      font-size: 14px;
    }}
    th {{
      color: var(--muted);
      font: 700 12px/1.2 Consolas, "Courier New", monospace;
      text-transform: uppercase;
      background: #eef1eb;
    }}
    tbody tr:hover {{ background: #faf8f1; }}
    code {{
      font-family: Consolas, "Courier New", monospace;
      font-size: 13px;
    }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 10px;
    }}
    .metric {{
      border-left: 4px solid var(--accent);
      background: var(--panel);
      padding: 10px 12px;
    }}
    .metric strong {{
      display: block;
      margin-bottom: 6px;
      color: var(--accent);
    }}
    .empty {{
      border: 1px dashed var(--line);
      padding: 14px;
      color: var(--muted);
      background: rgba(255, 255, 255, 0.55);
    }}
    .export-panel {{
      display: grid;
      gap: 10px;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 14px;
      background: rgba(255, 255, 255, 0.55);
    }}
    .export-panel h3 {{
      margin: 0;
      font-size: 16px;
    }}
    .export-output {{
      min-height: 260px;
      white-space: pre;
    }}
    .button-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }}
    button {{
      border: 1px solid var(--accent);
      border-radius: 4px;
      padding: 8px 10px;
      background: var(--accent);
      color: #ffffff;
      font: 700 12px/1.2 Consolas, "Courier New", monospace;
      text-transform: uppercase;
      cursor: pointer;
    }}
    button.secondary {{
      background: #ffffff;
      color: var(--accent);
    }}
    button:disabled {{
      border-color: var(--line);
      background: #e4e7e1;
      color: var(--muted);
      cursor: not-allowed;
    }}
    .status {{
      margin: 10px 0;
      color: var(--muted);
      font: 13px/1.45 Consolas, "Courier New", monospace;
    }}
    .status.error {{ color: var(--warn); }}
    .status.ok {{ color: var(--ok); }}
    .validation-list {{
      margin: 10px 0 0;
      padding-left: 22px;
      color: var(--warn);
      font: 13px/1.45 Consolas, "Courier New", monospace;
    }}
    .validation-list:empty {{ display: none; }}
    @media (max-width: 760px) {{
      header, .grid, .subgrid {{ grid-template-columns: 1fr; }}
      h1 {{ font-size: 28px; }}
      th, td {{ font-size: 13px; }}
    }}
  </style>
</head>
<body>
<main>
  <header>
    <div>
      <h1>context-eval local UI</h1>
    </div>
    <div class="stamp">run {escape(str(run_id))}</div>
  </header>
  {_config_section(config, tasks, editor)}
  {_preflight_section(config, editor)}
  {_persistence_section()}
  {_matrix_section(editor)}
  {_export_section(config, editor)}
  {_run_overview_section(results)}
  {_large_matrix_cells_section(results)}
  {_metrics_section(results)}
  {_agent_metrics_section(results)}
  {_results_section(results)}
</main>
{_editor_script(editor)}
</body>
</html>
"""


def _config_section(
    config: ContextEvalConfig | None,
    tasks: TaskFile | None,
    editor: EditableConfigModel | None,
) -> str:
    if config is None or tasks is None or editor is None:
        return _empty_section("Configuration", "No config file loaded.")

    evaluation_commands = "\n".join(editor.evaluation_commands)
    evaluation_timeout_seconds = (
        "" if editor.evaluation_timeout_seconds is None else str(editor.evaluation_timeout_seconds)
    )

    return f"""
<div data-role="config-editor">
<section>
  <h2>Configuration</h2>
  <div class="grid">
    {_input("Repo path", editor.repo.path, "repo.path")}
    {_input("Base ref", editor.repo.base_ref, "repo.base_ref")}
    {_input("Agent name", editor.agent.name, "agent.name")}
    {_select(
        "Agent kind",
        editor.agent.kind,
        "agent.kind",
        ["coco", "custom", "codex-cli", "claude-code", "traecli"],
    )}
    {_input("Agent command", editor.agent.command, "agent.command")}
    {_input(
        "Agent timeout minutes",
        str(editor.agent.timeout_minutes),
        "agent.timeout_minutes",
        input_type="number",
    )}
    {_select("Agent network", editor.agent.network, "agent.network", ["disabled", "enabled"])}
    {_input("Tasks file", editor.tasks_path, "tasks_path")}
    {_textarea("Validation commands", evaluation_commands, "evaluation_commands")}
    {_input(
        "Validation timeout seconds",
        evaluation_timeout_seconds,
        "evaluation_timeout_seconds",
        input_type="number",
    )}
  </div>
  <div class="resolved">Resolved repo: <code>{escape(str(config.repo.path))}</code></div>
</section>
<section>
  <h2>Variants</h2>
  {''.join(_variant_editor(index, variant) for index, variant in enumerate(editor.variants))}
</section>
<section>
  <h2>Tasks</h2>
  {''.join(_task_editor(index, task) for index, task in enumerate(editor.tasks))}
</section>
</div>
"""


def _matrix_section(editor: EditableConfigModel | None) -> str:
    if editor is None:
        return _empty_section("Agent x Task x Variant Matrix", "No matrix available.")

    return f"""
<section>
  <h2>Agent x Task x Variant Matrix</h2>
  <table>
    <thead>
      <tr><th>Agent</th><th>Task</th><th>Variant</th><th>Repo ref</th><th>Prompt path</th></tr>
    </thead>
    <tbody id="matrix-body">{_matrix_rows(editor)}</tbody>
  </table>
</section>
"""


def _export_section(
    config: ContextEvalConfig | None,
    editor: EditableConfigModel | None,
) -> str:
    if config is None or editor is None:
        return _empty_section("Export YAML", "No editable config loaded.")

    validate_command = _validate_config_command(config)

    return f"""
<section data-role="yaml-export">
  <h2>Export YAML</h2>
  <div id="export-status" class="status" aria-live="polite"></div>
  <div class="grid">
    <div class="export-panel">
      <h3>context-eval.yaml</h3>
      <textarea
        id="config-yaml-export"
        class="export-output"
        readonly
        spellcheck="false"
      ></textarea>
      <div class="button-row">
        <button type="button" class="secondary" data-copy-target="config-yaml-export">
          Copy
        </button>
        <button
          type="button"
          data-download-target="config-yaml-export"
          data-filename="context-eval.yaml"
        >
          Download
        </button>
      </div>
      <div id="config-yaml-message" class="status" aria-live="polite"></div>
    </div>
    <div class="export-panel">
      <h3>tasks.yaml</h3>
      <textarea id="tasks-yaml-export" class="export-output" readonly spellcheck="false"></textarea>
      <div class="button-row">
        <button type="button" class="secondary" data-copy-target="tasks-yaml-export">
          Copy
        </button>
        <button type="button" data-download-target="tasks-yaml-export" data-filename="tasks.yaml">
          Download
        </button>
      </div>
      <div id="tasks-yaml-message" class="status" aria-live="polite"></div>
    </div>
  </div>
  <div class="resolved">
    Static mode cannot save directly to disk. Copy or download both files, then run
    <code>{escape(validate_command)}</code>.
  </div>
</section>
"""


def _preflight_section(
    config: ContextEvalConfig | None,
    editor: EditableConfigModel | None,
) -> str:
    if config is None or editor is None:
        return _empty_section("Validation Preflight", "No editable config loaded.")

    validate_command = _validate_config_command(config)

    return f"""
<section data-role="validation-preflight">
  <h2>Validation Preflight</h2>
  <div id="preflight-status" class="status" aria-live="polite"></div>
  <ul id="preflight-issues" class="validation-list" aria-live="polite"></ul>
  <div class="resolved">
    Full local validation: <code id="validate-config-command">{escape(validate_command)}</code>
  </div>
  <div class="resolved">
    Static mode does not run agents, validation commands, workspaces, or network actions.
  </div>
</section>
"""


def _persistence_section() -> str:
    return """
<section
  data-role="persistence-mode"
  data-persistence-mode="static-export-only"
  data-server-mode="disabled"
>
  <h2>Persistence</h2>
  <div class="metrics">
    <div class="metric">
      <strong>Mode: static export-only</strong>
      <code>copy/download YAML only</code>
    </div>
    <div class="metric">
      <strong>Server endpoints: disabled</strong>
      <code>no sockets or local HTTP handlers</code>
    </div>
    <div class="metric">
      <strong>Direct file writes: disabled</strong>
      <code>browser download is the only write-adjacent action</code>
    </div>
    <div class="metric">
      <strong>Agent and validation execution: disabled</strong>
      <code>run validate-config outside this page</code>
    </div>
  </div>
</section>
"""


def _validate_config_command(config: ContextEvalConfig) -> str:
    config_path = str(config.config_path) if config.config_path is not None else "context-eval.yaml"
    return f"context-eval validate-config --config {config_path}"


def _matrix_rows(editor: EditableConfigModel) -> str:
    rows = []
    agents = editor.agents if editor.agent_shape == "agents" else [editor.agent]
    for agent in agents:
        for task in editor.tasks:
            for variant in editor.variants:
                repo_ref = task.repo_ref or editor.repo.base_ref
                case_id = f"{slugify(task.id)}__{slugify(variant.name)}"
                if editor.agent_shape == "agents":
                    case_id = f"{case_id}__{slugify(agent.name)}"
                rows.append(
                    "<tr>"
                    f"<td><code>{escape(agent.name)}</code></td>"
                    f"<td><code>{escape(task.id)}</code></td>"
                    f"<td><code>{escape(variant.name)}</code></td>"
                    f"<td><code>{escape(repo_ref)}</code></td>"
                    f"<td><code>prompts/{escape(case_id)}.md</code></td>"
                    "</tr>"
                )
    return "".join(rows)


def _run_overview_section(results: list[CaseResult]) -> str:
    if not results:
        return _empty_section("Run Matrix Overview", "No run results loaded.")

    overview = run_matrix_overview(results)
    metrics = [
        ("tasks", overview["task_count"]),
        ("variants", overview["variant_count"]),
        ("agents", overview["agent_count"]),
        ("trials", overview["trial_count"]),
        ("cases", overview["case_count"]),
        ("failed", overview["failed_count"]),
        ("timeouts", overview["timeout_count"]),
        ("low_confidence", overview["low_confidence_count"]),
        ("telemetry_gaps", overview["telemetry_gap_count"]),
    ]
    cards = "".join(
        '<div class="metric">'
        f"<strong>{escape(label)}</strong>"
        f"<code>{escape(label)}={value}</code>"
        "</div>"
        for label, value in metrics
    )
    return f"""
<section>
  <h2>Run Matrix Overview</h2>
  <div class="resolved">
    Local observations only; sourced from results.jsonl and optional run_metadata.json.
    <code>{escape(format_matrix_overview_inline(overview))}</code>
  </div>
  <div class="metrics">{cards}</div>
</section>
"""


def _large_matrix_cells_section(results: list[CaseResult]) -> str:
    if not results:
        return ""

    rows = []
    for cell in matrix_cell_rows(results):
        rows.append(
            "<tr>"
            f"<td><code>{escape(str(cell['task_id']))}</code></td>"
            f"<td><code>{escape(str(cell['variant']))}</code></td>"
            f"<td>{int(cell['cases'])}</td>"
            f"<td>{float(cell['pass_rate']):.1%}</td>"
            f"<td><code>{escape(str(cell['status_counts']))}</code></td>"
            f"<td><code>{escape(str(cell['validation_counts']))}</code></td>"
            f"<td><code>{escape(str(cell['confidence_counts']))}</code></td>"
            f"<td><code>{escape(str(cell['agents']))}</code></td>"
            f"<td><code>{escape(str(cell['trials']))}</code></td>"
            f"<td><code>{escape(str(cell['summary']))}</code></td>"
            "</tr>"
        )
    return f"""
<section>
  <h2>Large Matrix Cells</h2>
  <table>
    <thead>
      <tr>
        <th>Task</th><th>Variant</th><th>Cases</th><th>Pass rate</th>
        <th>Status counts</th><th>Validation counts</th><th>Confidence counts</th>
        <th>Agents</th><th>Trials</th><th>Summary</th>
      </tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</section>
"""


def _metrics_section(results: list[CaseResult]) -> str:
    if not results:
        return _empty_section("Variant Metrics", "No run results loaded.")

    metrics = []
    for stat in _variant_stats(results):
        metrics.append(
            '<div class="metric">'
            f"<strong>{escape(str(stat['variant']))}</strong>"
            f"<code>pass_rate={float(stat['pass_rate']):.1%}</code><br>"
            f"<code>timeout_rate={float(stat['timeout_rate']):.1%}</code><br>"
            f"<code>agent_failure_rate={float(stat['agent_failure_rate']):.1%}</code><br>"
            f"<code>validation_failure_rate={float(stat['validation_failure_rate']):.1%}</code><br>"
            f"<code>avg_duration={float(stat['avg_duration']):.2f}</code><br>"
            f"<code>avg_changed_files={float(stat['avg_changed_files']):.2f}</code><br>"
            f"<code>common_touched_paths={escape(str(stat['common_touched_paths']))}</code><br>"
            f"<code>telemetry_statuses={escape(str(stat['telemetry_statuses']))}</code><br>"
            f"<code>avg_agent_duration="
            f"{format_optional_number(stat['avg_agent_duration_seconds'])}</code><br>"
            f"<code>avg_total_tokens="
            f"{format_optional_number(stat['avg_total_tokens'])}</code><br>"
            f"<code>avg_tool_calls={format_optional_number(stat['avg_tool_calls'])}</code><br>"
            f"<code>common_tool_names={escape(str(stat['common_tool_names']))}</code>"
            "</div>"
        )
    return f"""
<section>
  <h2>Variant Metrics</h2>
  <div class="metrics">{''.join(metrics)}</div>
</section>
"""


def _agent_metrics_section(results: list[CaseResult]) -> str:
    if not results or not has_multiple_agents(results):
        return ""

    metrics = []
    for stat in agent_summary_rows(results):
        metrics.append(
            '<div class="metric">'
            f"<strong>{escape(str(stat['agent_name']))}</strong>"
            f"<code>cases={int(stat['cases'])}</code><br>"
            f"<code>pass_rate={float(stat['pass_rate']):.1%}</code><br>"
            f"<code>avg_duration={format_optional_number(stat['avg_duration_seconds'])}</code><br>"
            f"<code>avg_agent_duration="
            f"{format_optional_number(stat['avg_agent_duration_seconds'])}</code><br>"
            f"<code>avg_total_tokens={format_optional_number(stat['avg_total_tokens'])}</code><br>"
            f"<code>avg_tool_calls={format_optional_number(stat['avg_tool_call_count'])}</code><br>"
            f"<code>telemetry_statuses="
            f"{escape(format_status_counts(stat['telemetry_statuses']))}</code><br>"
            f"<code>common_tool_names="
            f"{escape(','.join(stat['common_tool_names']) or '-')}</code>"
            "</div>"
        )
    return f"""
<section>
  <h2>Agent Metrics</h2>
  <div class="metrics">{''.join(metrics)}</div>
</section>
"""


def _results_section(results: list[CaseResult]) -> str:
    if not results:
        return _empty_section("Run Results", "No result rows loaded.")

    rows = []
    for result in results:
        rows.append(
            "<tr>"
            f"<td><code>{escape(result.case_id or '')}</code></td>"
            f"<td><code>{escape(result.task_id)}</code></td>"
            f"<td><code>{escape(result.variant)}</code></td>"
            f"<td><code>{escape(result.agent_name)}</code></td>"
            f"<td>{result.trial_index}</td>"
            f"<td><code>{escape(result.status)}</code></td>"
            f"<td><code>{escape(result.validation_status)}</code></td>"
            f"<td><code>{escape(result.confidence)}</code></td>"
            f"<td><code>{escape(result.telemetry_status)}</code></td>"
            f"<td>{format_optional_number(result.agent_duration_seconds)}</td>"
            f"<td>{format_optional_int(result.total_tokens)}</td>"
            f"<td>{format_optional_int(result.tool_call_count)}</td>"
            f"<td>{result.changed_files}</td>"
            "</tr>"
        )
    return f"""
<section>
  <h2>Run Results</h2>
  <table>
    <thead>
      <tr>
        <th>Case</th><th>Task</th><th>Variant</th><th>Agent</th><th>Trial</th>
        <th>Status</th><th>Validation</th><th>Confidence</th><th>Telemetry</th>
        <th>Agent duration</th><th>Total tokens</th><th>Tool calls</th><th>Changed</th>
      </tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</section>
"""


def _input(
    label: str,
    value: str,
    field: str,
    *,
    input_type: str = "text",
    data: dict[str, str | int] | None = None,
) -> str:
    return (
        f'<label>{escape(label)}'
        f'<input type="{escape(input_type, quote=True)}" value="{escape(value, quote=True)}" '
        f'data-field="{escape(field, quote=True)}"{_data_attrs(data)} spellcheck="false">'
        "</label>"
    )


def _textarea(
    label: str,
    value: str,
    field: str,
    *,
    data: dict[str, str | int] | None = None,
) -> str:
    return (
        f'<label>{escape(label)}'
        f'<textarea data-field="{escape(field, quote=True)}"{_data_attrs(data)} '
        f'spellcheck="false">{escape(value)}</textarea>'
        "</label>"
    )


def _select(label: str, value: str, field: str, options: list[str]) -> str:
    if value not in options:
        options = [value, *options]
    rendered_options = "".join(
        f'<option value="{escape(option, quote=True)}"'
        f'{" selected" if option == value else ""}>{escape(option)}</option>'
        for option in options
    )
    return (
        f'<label>{escape(label)}'
        f'<select data-field="{escape(field, quote=True)}">{rendered_options}</select>'
        "</label>"
    )


def _empty_section(title: str, message: str) -> str:
    return (
        f"<section><h2>{escape(title)}</h2>"
        f'<div class="empty">{escape(message)}</div></section>'
    )


def _variant_editor(index: int, variant) -> str:
    data = {"variant-index": index}
    return f"""
  <fieldset>
    <legend>Variant {index + 1}</legend>
    <div class="grid">
      {_input("Name", variant.name, "variant.name", data=data)}
      {_textarea("Description", variant.description, "variant.description", data=data)}
    </div>
    {_overlay_editors(index, variant.overlays)}
  </fieldset>
"""


def _overlay_editors(variant_index: int, overlays) -> str:
    if not overlays:
        return '<div class="empty">No overlays configured.</div>'
    rendered = []
    for overlay_index, overlay in enumerate(overlays):
        data = {"variant-index": variant_index, "overlay-index": overlay_index}
        rendered.append(
            '<div class="subgrid">'
            f'{_input("Overlay source", overlay.source, "overlay.source", data=data)}'
            f'{_input("Overlay target", overlay.target, "overlay.target", data=data)}'
            "</div>"
        )
    return "".join(rendered)


def _task_editor(index: int, task) -> str:
    data = {"task-index": index}
    task_validation_commands = "\n".join(task.validation_commands)
    task_validation_timeout_seconds = (
        ""
        if task.validation_timeout_seconds is None
        else str(task.validation_timeout_seconds)
    )
    return f"""
  <fieldset>
    <legend>Task {index + 1}</legend>
    <div class="grid">
      {_input("ID", task.id, "task.id", data=data)}
      {_input("Title", task.title or "", "task.title", data=data)}
      {_input("Repo ref", task.repo_ref or "", "task.repo_ref", data=data)}
      {_input("Category", task.category or "", "task.category", data=data)}
      {_input("Difficulty", task.difficulty or "", "task.difficulty", data=data)}
      {_input(
        "Task validation timeout seconds",
        task_validation_timeout_seconds,
        "task.validation_timeout_seconds",
        input_type="number",
        data=data,
    )}
      {_textarea(
        "Task validation commands",
        task_validation_commands,
        "task.validation_commands",
        data=data,
    )}
    </div>
    {_textarea("Prompt", task.prompt, "task.prompt", data=data)}
  </fieldset>
"""


def _data_attrs(data: dict[str, str | int] | None) -> str:
    if not data:
        return ""
    return "".join(
        f' data-{escape(str(key), quote=True)}="{escape(str(value), quote=True)}"'
        for key, value in data.items()
    )


def _editor_script(editor: EditableConfigModel | None) -> str:
    if editor is None:
        return ""

    return f"""
<script type="application/json" id="editable-model">{_json_script_data(editor)}</script>
<script>
(() => {{
  const modelNode = document.getElementById("editable-model");
  if (!modelNode) {{
    return;
  }}

  const editableModel = JSON.parse(modelNode.textContent);

  function splitLines(value) {{
    return String(value)
      .split(/\\r?\\n/)
      .map((line) => line.trim())
      .filter((line) => line.length > 0);
  }}

  function optionalText(value) {{
    const trimmed = String(value).trim();
    return trimmed.length > 0 ? trimmed : null;
  }}

  function optionalPositiveInteger(value) {{
    const trimmed = String(value ?? "").trim();
    if (trimmed.length === 0) {{
      return null;
    }}
    const parsed = Number.parseInt(trimmed, 10);
    return Number.isFinite(parsed) && parsed >= 1 ? parsed : null;
  }}

  function slugify(value) {{
    const slug = String(value).replace(/[^A-Za-z0-9_.-]+/g, "-").replace(/^-+|-+$/g, "");
    return slug || "case";
  }}

  function yamlInlineString(value) {{
    return JSON.stringify(String(value ?? ""));
  }}

  function yamlValue(value, indent) {{
    const text = String(value ?? "");
    if (!text.includes("\\n")) {{
      return yamlInlineString(text);
    }}

    const spaces = " ".repeat(indent + 2);
    const lines = text.replace(/\\r\\n/g, "\\n").split("\\n");
    return "|\\n" + lines.map((line) => spaces + line).join("\\n");
  }}

  function yamlKey(value) {{
    return yamlInlineString(value);
  }}

  function appendYamlField(lines, indent, key, value) {{
    if (value === null || value === undefined) {{
      return;
    }}
    lines.push(" ".repeat(indent) + key + ": " + yamlValue(value, indent));
  }}

  function appendYamlList(lines, indent, key, values) {{
    const spaces = " ".repeat(indent);
    if (!Array.isArray(values) || values.length === 0) {{
      lines.push(spaces + key + ": []");
      return;
    }}

    lines.push(spaces + key + ":");
    values.forEach((value) => {{
      lines.push(spaces + "  - " + yamlInlineString(value));
    }});
  }}

  function renderConfigYaml() {{
    const lines = [];
    lines.push("repo:");
    appendYamlField(lines, 2, "path", editableModel.repo.path);
    appendYamlField(lines, 2, "base_ref", editableModel.repo.base_ref);
    if (editableModel.agent_shape === "agents") {{
      lines.push("agents:");
      const agents = Array.isArray(editableModel.agents) && editableModel.agents.length > 0
        ? editableModel.agents
        : [editableModel.agent];
      agents.forEach((agent, index) => {{
        const profile = index === 0 ? editableModel.agent : agent;
        lines.push("  " + yamlKey(profile.name) + ":");
        appendYamlField(lines, 4, "kind", profile.kind || "custom");
        appendYamlField(lines, 4, "command", profile.command);
        lines.push(
          "    timeout_minutes: " +
            String(Number.parseInt(profile.timeout_minutes, 10) || 1)
        );
        appendYamlField(lines, 4, "network", profile.network);
      }});
    }} else {{
      lines.push("agent:");
      appendYamlField(lines, 2, "name", editableModel.agent.name);
      appendYamlField(lines, 2, "command", editableModel.agent.command);
      lines.push(
        "  timeout_minutes: " +
          String(Number.parseInt(editableModel.agent.timeout_minutes, 10) || 1)
      );
      appendYamlField(lines, 2, "network", editableModel.agent.network);
    }}
    appendYamlField(lines, 0, "tasks", editableModel.tasks_path);
    if (editableModel.output_dir !== null && editableModel.output_dir !== undefined) {{
      appendYamlField(lines, 0, "output_dir", editableModel.output_dir);
    }}
    lines.push("variants:");
    editableModel.variants.forEach((variant) => {{
      lines.push("  " + yamlKey(variant.name) + ":");
      appendYamlField(lines, 4, "description", variant.description);
      if (!Array.isArray(variant.overlays) || variant.overlays.length === 0) {{
        lines.push("    overlays: []");
      }} else {{
        lines.push("    overlays:");
        variant.overlays.forEach((overlay) => {{
          lines.push("      - source: " + yamlValue(overlay.source, 8));
          appendYamlField(lines, 8, "target", overlay.target);
        }});
      }}
    }});
    lines.push("evaluation:");
    if (editableModel.evaluation_timeout_seconds !== null &&
        editableModel.evaluation_timeout_seconds !== undefined) {{
      lines.push(
        "  timeout_seconds: " +
          String(Number.parseInt(editableModel.evaluation_timeout_seconds, 10) || 1)
      );
    }}
    appendYamlList(lines, 2, "commands", editableModel.evaluation_commands);
    return lines.join("\\n") + "\\n";
  }}

  function renderTasksYaml() {{
    const lines = ["tasks:"];
    editableModel.tasks.forEach((task) => {{
      lines.push("  - id: " + yamlValue(task.id, 4));
      appendYamlField(lines, 4, "title", task.title);
      appendYamlField(lines, 4, "prompt", task.prompt);
      appendYamlField(lines, 4, "repo_ref", task.repo_ref);
      appendYamlField(lines, 4, "category", task.category);
      appendYamlField(lines, 4, "difficulty", task.difficulty);
      if (
        (Array.isArray(task.validation_commands) && task.validation_commands.length > 0) ||
        (task.validation_timeout_seconds !== null &&
          task.validation_timeout_seconds !== undefined)
      ) {{
        lines.push("    validation:");
        if (task.validation_timeout_seconds !== null &&
            task.validation_timeout_seconds !== undefined) {{
          lines.push(
            "      timeout_seconds: " +
              String(Number.parseInt(task.validation_timeout_seconds, 10) || 1)
          );
        }}
        appendYamlList(lines, 6, "commands", task.validation_commands);
      }}
    }});
    return lines.join("\\n") + "\\n";
  }}

  function isSafeRelativePath(value) {{
    const text = String(value ?? "").trim().replace(/\\\\/g, "/");
    if (text.length === 0) {{
      return false;
    }}
    if (text.startsWith("/") || /^[A-Za-z]:/.test(text)) {{
      return false;
    }}
    return !text.split("/").includes("..");
  }}

  function validateEditedConfiguration() {{
    const issues = [];

    function requireText(value, label) {{
      if (String(value ?? "").trim().length === 0) {{
        issues.push(label + " is required");
      }}
    }}

    requireText(editableModel.repo.path, "repo.path");
    requireText(editableModel.repo.base_ref, "repo.base_ref");
    requireText(editableModel.agent.name, "agent.name");
    requireText(editableModel.agent.command, "agent.command");
    if (
      !["custom", "codex-cli", "claude-code", "traecli", "coco"]
        .includes(String(editableModel.agent.kind))
    ) {{
      issues.push("agent.kind must be custom, codex-cli, claude-code, traecli, or coco");
    }}
    requireText(editableModel.tasks_path, "tasks path");

    const timeout = Number.parseInt(editableModel.agent.timeout_minutes, 10);
    if (!Number.isFinite(timeout) || timeout < 1) {{
      issues.push("agent.timeout_minutes must be a positive integer");
    }}
    if (!["disabled", "enabled"].includes(String(editableModel.agent.network))) {{
      issues.push("agent.network must be disabled or enabled");
    }}
    if (editableModel.agent_shape === "agents") {{
      const agents = Array.isArray(editableModel.agents) && editableModel.agents.length > 0
        ? editableModel.agents
        : [editableModel.agent];
      const agentNames = new Set();
      agents.forEach((agent, index) => {{
        const profile = index === 0 ? editableModel.agent : agent;
        const name = String(profile.name ?? "").trim();
        if (name.length === 0) {{
          issues.push("agent profile " + String(index + 1) + " name is required");
        }} else if (agentNames.has(name)) {{
          issues.push("duplicate agent profile: " + name);
        }} else {{
          agentNames.add(name);
        }}
        requireText(profile.command, "agent profile " + String(index + 1) + " command");
        if (
          !["custom", "codex-cli", "claude-code", "traecli", "coco"]
            .includes(String(profile.kind))
        ) {{
          issues.push(
            "agent profile " + String(index + 1) +
              " kind must be custom, codex-cli, claude-code, traecli, or coco"
          );
        }}
      }});
    }}
    if (
      editableModel.evaluation_timeout_seconds !== null &&
      editableModel.evaluation_timeout_seconds !== undefined
    ) {{
      const evaluationTimeout = Number.parseInt(editableModel.evaluation_timeout_seconds, 10);
      if (!Number.isFinite(evaluationTimeout) || evaluationTimeout < 1) {{
        issues.push("evaluation.timeout_seconds must be a positive integer");
      }}
    }}

    if (!Array.isArray(editableModel.variants) || editableModel.variants.length === 0) {{
      issues.push("at least one variant is required");
    }}
    const variantNames = new Set();
    editableModel.variants.forEach((variant, index) => {{
      const name = String(variant.name ?? "").trim();
      if (name.length === 0) {{
        issues.push("variant " + String(index + 1) + " name is required");
      }} else if (variantNames.has(name)) {{
        issues.push("duplicate variant name: " + name);
      }} else {{
        variantNames.add(name);
      }}

      (variant.overlays || []).forEach((overlay, overlayIndex) => {{
        requireText(
          overlay.source,
          "variant " + String(index + 1) + " overlay " + String(overlayIndex + 1) + " source"
        );
        requireText(
          overlay.target,
          "variant " + String(index + 1) + " overlay " + String(overlayIndex + 1) + " target"
        );
        if (!isSafeRelativePath(overlay.target)) {{
          issues.push(
            "variant " +
              String(index + 1) +
              " overlay " +
              String(overlayIndex + 1) +
              " target must be a safe relative path"
          );
        }}
      }});
    }});

    if (!Array.isArray(editableModel.tasks) || editableModel.tasks.length === 0) {{
      issues.push("at least one task is required");
    }}
    const taskIds = new Set();
    editableModel.tasks.forEach((task, index) => {{
      const id = String(task.id ?? "").trim();
      if (id.length === 0) {{
        issues.push("task " + String(index + 1) + " id is required");
      }} else if (taskIds.has(id)) {{
        issues.push("duplicate task id: " + id);
      }} else {{
        taskIds.add(id);
      }}
      requireText(task.prompt, "task " + String(index + 1) + " prompt");
      if (
        task.validation_timeout_seconds !== null &&
        task.validation_timeout_seconds !== undefined
      ) {{
        const taskTimeout = Number.parseInt(task.validation_timeout_seconds, 10);
        if (!Number.isFinite(taskTimeout) || taskTimeout < 1) {{
          issues.push(
            "task " + String(index + 1) +
              " validation.timeout_seconds must be a positive integer"
          );
        }}
      }}
    }});

    return issues;
  }}

  function validateExportModel() {{
    return validateEditedConfiguration();
  }}

  function validateGeneratedYaml(configYaml, tasksYaml) {{
    const issues = [];
    [
      [
        configYaml,
        "config export",
        [
          "repo:",
          editableModel.agent_shape === "agents" ? "agents:" : "agent:",
          "tasks:",
          "variants:",
        ]
      ],
      [tasksYaml, "tasks export", ["tasks:"]],
    ].forEach(([content, label, requiredMarkers]) => {{
      requiredMarkers.forEach((marker) => {{
        if (!content.includes(marker)) {{
          issues.push(label + " is missing " + marker);
        }}
      }});
      if (content.includes("undefined")) {{
        issues.push(label + " contains undefined values");
      }}
    }});
    return issues;
  }}

  function setExportButtonsDisabled(disabled) {{
    document
      .querySelectorAll("[data-copy-target], [data-download-target]")
      .forEach((button) => {{
        button.disabled = disabled;
      }});
  }}

  function refreshValidationPreflight() {{
    const status = document.getElementById("preflight-status");
    const list = document.getElementById("preflight-issues");
    if (!status || !list) {{
      return;
    }}

    const issues = validateEditedConfiguration();
    list.textContent = "";
    if (issues.length === 0) {{
      status.textContent = "No schema-level issues detected in edited YAML.";
      status.classList.remove("error");
      status.classList.add("ok");
      return;
    }}

    status.textContent = "Schema preflight found " + String(issues.length) + " issue(s).";
    status.classList.remove("ok");
    status.classList.add("error");
    issues.forEach((issue) => {{
      const item = document.createElement("li");
      item.textContent = issue;
      list.appendChild(item);
    }});
  }}

  function refreshExport() {{
    const status = document.getElementById("export-status");
    const configOutput = document.getElementById("config-yaml-export");
    const tasksOutput = document.getElementById("tasks-yaml-export");
    if (!status || !configOutput || !tasksOutput) {{
      return;
    }}

    const modelIssues = validateExportModel();
    if (modelIssues.length > 0) {{
      configOutput.value = "";
      tasksOutput.value = "";
      status.textContent = "Export blocked: " + modelIssues.join("; ");
      status.classList.add("error");
      setExportButtonsDisabled(true);
      return;
    }}

    const configYaml = renderConfigYaml();
    const tasksYaml = renderTasksYaml();
    const yamlIssues = validateGeneratedYaml(configYaml, tasksYaml);
    if (yamlIssues.length > 0) {{
      configOutput.value = "";
      tasksOutput.value = "";
      status.textContent = "Export blocked: " + yamlIssues.join("; ");
      status.classList.add("error");
      setExportButtonsDisabled(true);
      return;
    }}

    configOutput.value = configYaml;
    tasksOutput.value = tasksYaml;
    status.textContent = "Export ready. Review both YAML documents before copying or downloading.";
    status.classList.remove("error");
    setExportButtonsDisabled(false);
  }}

  function setExportMessage(targetId, message, isError = false) {{
    const messageId = targetId === "config-yaml-export"
      ? "config-yaml-message"
      : "tasks-yaml-message";
    const node = document.getElementById(messageId);
    if (!node) {{
      return;
    }}
    node.textContent = message;
    node.classList.toggle("error", isError);
  }}

  function fallbackCopy(output, targetId) {{
    output.focus();
    output.select();
    try {{
      const copied = document.execCommand("copy");
      setExportMessage(
        targetId,
        copied ? "Copied to clipboard." : "Clipboard copy is unavailable.",
        !copied
      );
    }} catch (error) {{
      setExportMessage(targetId, "Clipboard copy is unavailable.", true);
    }}
    window.getSelection()?.removeAllRanges();
  }}

  function copyYaml(targetId) {{
    const output = document.getElementById(targetId);
    if (!output || output.value.length === 0) {{
      return;
    }}

    if (navigator.clipboard && window.isSecureContext) {{
      navigator.clipboard
        .writeText(output.value)
        .then(() => setExportMessage(targetId, "Copied to clipboard."))
        .catch(() => fallbackCopy(output, targetId));
      return;
    }}

    fallbackCopy(output, targetId);
  }}

  function downloadYaml(targetId, filename) {{
    const output = document.getElementById(targetId);
    if (!output || output.value.length === 0) {{
      return;
    }}

    const blob = new Blob([output.value], {{ type: "text/yaml;charset=utf-8" }});
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.setTimeout(() => URL.revokeObjectURL(url), 0);
    setExportMessage(targetId, "Download prepared by the browser.");
  }}

  function syncModelFromInputs() {{
    document
      .querySelectorAll('[data-role="config-editor"] [data-field]')
      .forEach((control) => {{
        const field = control.dataset.field;
        const value = control.value;

        if (field === "repo.path") {{
          editableModel.repo.path = value;
        }} else if (field === "repo.base_ref") {{
          editableModel.repo.base_ref = value;
        }} else if (field === "agent.name") {{
          editableModel.agent.name = value;
          if (editableModel.agent_shape === "agents" && editableModel.agents?.[0]) {{
            editableModel.agents[0].name = value;
          }}
        }} else if (field === "agent.kind") {{
          editableModel.agent.kind = value;
          if (editableModel.agent_shape === "agents" && editableModel.agents?.[0]) {{
            editableModel.agents[0].kind = value;
          }}
        }} else if (field === "agent.command") {{
          editableModel.agent.command = value;
          if (editableModel.agent_shape === "agents" && editableModel.agents?.[0]) {{
            editableModel.agents[0].command = value;
          }}
        }} else if (field === "agent.timeout_minutes") {{
          editableModel.agent.timeout_minutes = Number.parseInt(value, 10) || 1;
          if (editableModel.agent_shape === "agents" && editableModel.agents?.[0]) {{
            editableModel.agents[0].timeout_minutes = editableModel.agent.timeout_minutes;
          }}
        }} else if (field === "agent.network") {{
          editableModel.agent.network = value;
          if (editableModel.agent_shape === "agents" && editableModel.agents?.[0]) {{
            editableModel.agents[0].network = value;
          }}
        }} else if (field === "tasks_path") {{
          editableModel.tasks_path = value;
        }} else if (field === "evaluation_commands") {{
          editableModel.evaluation_commands = splitLines(value);
        }} else if (field === "evaluation_timeout_seconds") {{
          editableModel.evaluation_timeout_seconds = optionalPositiveInteger(value);
        }} else if (field === "variant.name" || field === "variant.description") {{
          const variant = editableModel.variants[Number(control.dataset.variantIndex)];
          if (variant) {{
            variant[field.split(".")[1]] = value;
          }}
        }} else if (field === "overlay.source" || field === "overlay.target") {{
          const variant = editableModel.variants[Number(control.dataset.variantIndex)];
          const overlay = variant?.overlays[Number(control.dataset.overlayIndex)];
          if (overlay) {{
            overlay[field.split(".")[1]] = value;
          }}
        }} else if (field.startsWith("task.")) {{
          const task = editableModel.tasks[Number(control.dataset.taskIndex)];
          if (task) {{
            const key = field.split(".")[1];
            if (key === "validation_commands") {{
              task[key] = splitLines(value);
            }} else if (key === "validation_timeout_seconds") {{
              task[key] = optionalPositiveInteger(value);
            }} else {{
              task[key] = optionalText(value);
            }}
            if (key === "id" || key === "prompt") {{
              task[key] = value;
            }}
          }}
        }}
      }});

    renderMatrix();
    refreshValidationPreflight();
    refreshExport();
  }}

  function appendCell(row, value) {{
    const cell = document.createElement("td");
    const code = document.createElement("code");
    code.textContent = value;
    cell.appendChild(code);
    row.appendChild(cell);
  }}

  function renderMatrix() {{
    const body = document.getElementById("matrix-body");
    if (!body) {{
      return;
    }}

    body.textContent = "";
    const agents = editableModel.agent_shape === "agents"
      ? (editableModel.agents || [editableModel.agent])
      : [editableModel.agent];
    agents.forEach((agent) => {{
      editableModel.tasks.forEach((task) => {{
        editableModel.variants.forEach((variant) => {{
          const agentName = agent.name || "agent";
          const taskId = task.id || "task";
          const variantName = variant.name || "variant";
          const repoRef = task.repo_ref || editableModel.repo.base_ref;
          let caseId = `${{slugify(taskId)}}__${{slugify(variantName)}}`;
          if (editableModel.agent_shape === "agents") {{
            caseId = `${{caseId}}__${{slugify(agentName)}}`;
          }}
        const row = document.createElement("tr");
        appendCell(row, agentName);
        appendCell(row, taskId);
        appendCell(row, variantName);
        appendCell(row, repoRef);
        appendCell(row, `prompts/${{caseId}}.md`);
        body.appendChild(row);
      }});
    }});
    }});
  }}

  document
    .querySelectorAll('[data-role="config-editor"] [data-field]')
    .forEach((control) => {{
      control.addEventListener("input", syncModelFromInputs);
      control.addEventListener("change", syncModelFromInputs);
    }});

  document.querySelectorAll("[data-copy-target]").forEach((button) => {{
    button.addEventListener("click", () => copyYaml(button.dataset.copyTarget));
  }});

  document.querySelectorAll("[data-download-target]").forEach((button) => {{
    button.addEventListener("click", () => {{
      downloadYaml(button.dataset.downloadTarget, button.dataset.filename || "context-eval.yaml");
    }});
  }});

  syncModelFromInputs();
}})();
</script>
"""


def _json_script_data(editor: EditableConfigModel) -> str:
    raw = json.dumps(editor.model_dump(mode="json"), ensure_ascii=True)
    return raw.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
