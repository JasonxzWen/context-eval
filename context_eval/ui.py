from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

from context_eval.compare import _variant_stats
from context_eval.config import ConfigError, validate_config_files
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
    input, textarea {{
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
      header, .grid {{ grid-template-columns: 1fr; }}
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
  {_config_section(config, tasks)}
  {_matrix_section(config, tasks)}
  {_metrics_section(results)}
  {_results_section(results)}
</main>
</body>
</html>
"""


def _config_section(config: ContextEvalConfig | None, tasks: TaskFile | None) -> str:
    if config is None or tasks is None:
        return _empty_section("Configuration", "No config file loaded.")

    validation_commands = "\n".join(config.evaluation.commands) or "none"
    task_ids = "\n".join(task.id for task in tasks.tasks)

    return f"""
<section>
  <h2>Configuration</h2>
  <div class="grid">
    {_input("Repo path", str(config.repo.path))}
    {_input("Base ref", config.repo.base_ref)}
    {_input("Agent command", config.agent.command)}
    {_input("Agent timeout minutes", str(config.agent.timeout_minutes))}
    {_textarea("Validation commands", validation_commands)}
    {_textarea("Tasks", task_ids)}
  </div>
</section>
<section>
  <h2>Variants</h2>
  <table>
    <thead><tr><th>Name</th><th>Description</th><th>Overlays</th></tr></thead>
    <tbody>
      {''.join(_variant_row(name, variant) for name, variant in config.variants.items())}
    </tbody>
  </table>
</section>
"""


def _matrix_section(config: ContextEvalConfig | None, tasks: TaskFile | None) -> str:
    if config is None or tasks is None:
        return _empty_section("Task x Variant Matrix", "No matrix available.")

    rows = []
    for task in tasks.tasks:
        for variant_name in config.variants:
            repo_ref = task.repo_ref or config.repo.base_ref
            case_id = f"{slugify(task.id)}__{slugify(variant_name)}"
            rows.append(
                "<tr>"
                f"<td><code>{escape(task.id)}</code></td>"
                f"<td><code>{escape(variant_name)}</code></td>"
                f"<td><code>{escape(repo_ref)}</code></td>"
                f"<td><code>prompts/{escape(case_id)}.md</code></td>"
                "</tr>"
            )
    return f"""
<section>
  <h2>Task x Variant Matrix</h2>
  <table>
    <thead><tr><th>Task</th><th>Variant</th><th>Repo ref</th><th>Prompt path</th></tr></thead>
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
      <tr><th>Case</th><th>Task</th><th>Variant</th><th>Trial</th><th>Status</th><th>Validation</th><th>Confidence</th><th>Changed</th></tr>
    </thead>
    <tbody>{''.join(rows)}</tbody>
  </table>
</section>
"""


def _input(label: str, value: str) -> str:
    return (
        f'<label>{escape(label)}'
        f'<input value="{escape(value, quote=True)}" spellcheck="false">'
        "</label>"
    )


def _textarea(label: str, value: str) -> str:
    return (
        f'<label>{escape(label)}'
        f"<textarea spellcheck=\"false\">{escape(value)}</textarea>"
        "</label>"
    )


def _variant_row(name, variant) -> str:
    overlays = ", ".join(
        f"{overlay.source.name} -> {overlay.target}" for overlay in variant.overlays
    )
    return (
        "<tr>"
        f"<td><code>{escape(name)}</code></td>"
        f"<td>{escape(variant.description)}</td>"
        f"<td><code>{escape(overlays or 'none')}</code></td>"
        "</tr>"
    )


def _empty_section(title: str, message: str) -> str:
    return (
        f"<section><h2>{escape(title)}</h2>"
        f'<div class="empty">{escape(message)}</div></section>'
    )
