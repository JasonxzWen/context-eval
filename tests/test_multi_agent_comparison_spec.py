from pathlib import Path


def test_multi_agent_comparison_spec_defines_contract() -> None:
    spec = Path("docs/multi-agent-comparison.md").read_text(encoding="utf-8")

    for heading in [
        "## User Contract",
        "## Source Artifacts",
        "## Comparison Dimensions",
        "## Export Formats",
        "## Reporting Behavior",
        "## Static UI Behavior",
        "## Non-Goals",
        "## Test Plan",
    ]:
        assert heading in spec

    for term in [
        "results.jsonl",
        "run_metadata.json",
        "agent_name",
        "task_id",
        "variant",
        "trial_index",
        "status",
        "validation_status",
        "confidence",
        "duration_seconds",
        "agent_duration_seconds",
        "prompt_tokens",
        "completion_tokens",
        "total_tokens",
        "reasoning_tokens",
        "tool_call_count",
        "tool_calls_by_name",
        "deterministic",
        "CSV",
        "compact JSON",
    ]:
        assert term in spec


def test_multi_agent_comparison_spec_documents_non_goals() -> None:
    spec = Path("docs/multi-agent-comparison.md").read_text(encoding="utf-8")

    for non_goal in [
        "LLM judge",
        "hosted dashboard",
        "multi-user web",
        "automatic coding-agent installation",
        "real network isolation",
        "absolute agent capability ranking",
    ]:
        assert non_goal in spec


def test_development_plan_links_multi_agent_comparison_spec() -> None:
    plan = Path("docs/development-plan.md").read_text(encoding="utf-8")

    assert "docs/multi-agent-comparison.md" in plan
    assert "CSV and compact JSON" in plan
    assert "not an absolute" in plan


def test_multi_agent_comparison_spec_documents_local_workflow_examples() -> None:
    spec = Path("docs/multi-agent-comparison.md").read_text(encoding="utf-8")

    for term in [
        "## Local Workflow Examples",
        "context-eval run --config",
        "agent.name",
        "context-eval inspect-run",
        "context-eval compare",
        "context-eval export",
        "--format csv",
        "--format json",
        "context-eval ui --run-dir",
        "Do not publish the output as an absolute leaderboard",
    ]:
        assert term in spec


def test_readme_mentions_export_commands() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    assert "context-eval export .context-eval/runs/<run-id> --format csv" in readme
    assert "context-eval export .context-eval/runs/<run-id> --format json" in readme


def test_readme_documents_compact_json_export_metadata() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")

    for term in [
        "Compact JSON export metadata",
        "export_schema_version",
        "exported_at",
        "source_files",
        "case_count",
        "agent_count",
        "variant_count",
        "task_count",
        "local observation",
    ]:
        assert term in readme


def test_compact_json_export_metadata_contract_is_documented() -> None:
    spec = Path("docs/multi-agent-comparison.md").read_text(encoding="utf-8")
    plan = Path("docs/development-plan.md").read_text(encoding="utf-8")

    for term in [
        "export_schema_version",
        "exported_at",
        "source_files",
        "case_count",
        "agent_count",
        "variant_count",
        "task_count",
        "run.metadata",
        "zero counts",
        "controllable timestamps",
    ]:
        assert term in spec

    assert "run_metadata.json` only when that optional file exists" in spec
    assert "results.jsonl` exists but contains no result rows" in spec
    assert "derived only from parsed `results.jsonl` rows" in spec
    assert "Harden compact JSON export metadata" in plan
    assert "controlled export timestamp" in plan
