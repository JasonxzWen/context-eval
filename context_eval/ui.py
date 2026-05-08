from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

from context_eval.compare import _variant_stats
from context_eval.config import ConfigError, validate_config_files
from context_eval.config_editor import EditableConfigModel, build_editable_model
from context_eval.inspect_run import _load_metadata, _load_results
from context_eval.models import CaseResult, ContextEvalConfig, TaskFile
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
  {_matrix_section(editor)}
  {_metrics_section(results)}
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

    return f"""
<div data-role="config-editor">
<section>
  <h2>Configuration</h2>
  <div class="grid">
    {_input("Repo path", editor.repo.path, "repo.path")}
    {_input("Base ref", editor.repo.base_ref, "repo.base_ref")}
    {_input("Agent name", editor.agent.name, "agent.name")}
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
        return _empty_section("Task x Variant Matrix", "No matrix available.")

    return f"""
<section>
  <h2>Task x Variant Matrix</h2>
  <table>
    <thead><tr><th>Task</th><th>Variant</th><th>Repo ref</th><th>Prompt path</th></tr></thead>
    <tbody id="matrix-body">{_matrix_rows(editor)}</tbody>
  </table>
</section>
"""


def _matrix_rows(editor: EditableConfigModel) -> str:
    rows = []
    for task in editor.tasks:
        for variant in editor.variants:
            repo_ref = task.repo_ref or editor.repo.base_ref
            case_id = f"{slugify(task.id)}__{slugify(variant.name)}"
            rows.append(
                "<tr>"
                f"<td><code>{escape(task.id)}</code></td>"
                f"<td><code>{escape(variant.name)}</code></td>"
                f"<td><code>{escape(repo_ref)}</code></td>"
                f"<td><code>prompts/{escape(case_id)}.md</code></td>"
                "</tr>"
            )
    return "".join(rows)


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
            f"<code>common_touched_paths={escape(str(stat['common_touched_paths']))}</code>"
            "</div>"
        )
    return f"""
<section>
  <h2>Variant Metrics</h2>
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
            f"<td>{result.trial_index}</td>"
            f"<td><code>{escape(result.status)}</code></td>"
            f"<td><code>{escape(result.validation_status)}</code></td>"
            f"<td><code>{escape(result.confidence)}</code></td>"
            f"<td>{result.changed_files}</td>"
            "</tr>"
        )
    return f"""
<section>
  <h2>Run Results</h2>
  <table>
    <thead>
      <tr>
        <th>Case</th><th>Task</th><th>Variant</th><th>Trial</th>
        <th>Status</th><th>Validation</th><th>Confidence</th><th>Changed</th>
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
    return f"""
  <fieldset>
    <legend>Task {index + 1}</legend>
    <div class="grid">
      {_input("ID", task.id, "task.id", data=data)}
      {_input("Title", task.title or "", "task.title", data=data)}
      {_input("Repo ref", task.repo_ref or "", "task.repo_ref", data=data)}
      {_input("Category", task.category or "", "task.category", data=data)}
      {_input("Difficulty", task.difficulty or "", "task.difficulty", data=data)}
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

  function slugify(value) {{
    const slug = String(value).replace(/[^A-Za-z0-9_.-]+/g, "-").replace(/^-+|-+$/g, "");
    return slug || "case";
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
        }} else if (field === "agent.command") {{
          editableModel.agent.command = value;
        }} else if (field === "agent.timeout_minutes") {{
          editableModel.agent.timeout_minutes = Number.parseInt(value, 10) || 1;
        }} else if (field === "agent.network") {{
          editableModel.agent.network = value;
        }} else if (field === "tasks_path") {{
          editableModel.tasks_path = value;
        }} else if (field === "evaluation_commands") {{
          editableModel.evaluation_commands = splitLines(value);
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
            task[key] = key === "validation_commands" ? splitLines(value) : optionalText(value);
            if (key === "id" || key === "prompt") {{
              task[key] = value;
            }}
          }}
        }}
      }});

    renderMatrix();
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
    editableModel.tasks.forEach((task) => {{
      editableModel.variants.forEach((variant) => {{
        const taskId = task.id || "task";
        const variantName = variant.name || "variant";
        const repoRef = task.repo_ref || editableModel.repo.base_ref;
        const caseId = `${{slugify(taskId)}}__${{slugify(variantName)}}`;
        const row = document.createElement("tr");
        appendCell(row, taskId);
        appendCell(row, variantName);
        appendCell(row, repoRef);
        appendCell(row, `prompts/${{caseId}}.md`);
        body.appendChild(row);
      }});
    }});
  }}

  document
    .querySelectorAll('[data-role="config-editor"] [data-field]')
    .forEach((control) => {{
      control.addEventListener("input", syncModelFromInputs);
      control.addEventListener("change", syncModelFromInputs);
    }});

  syncModelFromInputs();
}})();
</script>
"""


def _json_script_data(editor: EditableConfigModel) -> str:
    raw = json.dumps(editor.model_dump(mode="json"), ensure_ascii=True)
    return raw.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")
