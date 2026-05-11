from pathlib import Path


def test_local_ui_config_editor_spec_documents_contract() -> None:
    spec = Path("docs/local-ui-config-editor.md")
    assert spec.exists()

    text = spec.read_text(encoding="utf-8")

    required_headings = [
        "## User Contract",
        "## Persistence Decision",
        "## Editable Fields",
        "## Validation Behavior",
        "## Export And Save Behavior",
        "## User Workflow",
        "## Failure Modes",
        "## Edge Cases",
        "## Non-Goals",
        "## Test Plan",
    ]
    for heading in required_headings:
        assert heading in text

    required_terms = [
        "local-only",
        "context-eval.yaml",
        "tasks.yaml",
        "repo.path",
        "repo.base_ref",
        "agent.command",
        "evaluation.commands",
        "variants",
        "overlays",
        "tasks",
        "validate-config",
        "download",
        "copy",
        "static export-only",
        "no local server mode",
        "no server endpoints",
        "offline, self-contained HTML",
        "must not open sockets",
        "must not write local files",
        "no hosted service",
        "no remote database",
        "no LLM judge",
        "no agent run",
    ]
    for term in required_terms:
        assert term in text


def test_development_plan_links_local_ui_editor_spec() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")

    assert "docs/local-ui-config-editor.md" in text


def test_readme_documents_static_ui_persistence_workflow() -> None:
    text = Path("README.md").read_text(encoding="utf-8")
    normalized = " ".join(text.split())

    required_terms = [
        "static export-only",
        "copy or download",
        "does not save back to the original files",
        "does not run agents",
        "does not run validation commands",
        "context-eval validate-config --config",
    ]
    for term in required_terms:
        assert term in normalized
