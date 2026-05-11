from pathlib import Path


def _squash(text: str) -> str:
    return " ".join(text.split())


def test_config_diagnostics_spec_documents_contract() -> None:
    spec = Path("docs/config-diagnostics.md")
    assert spec.exists()

    text = spec.read_text(encoding="utf-8")

    for heading in [
        "## User Contract",
        "## Error Taxonomy",
        "## Diagnostic Context",
        "## Strict Validation",
        "## Non-Goals",
        "## Test Plan",
    ]:
        assert heading in text

    for term in [
        "field-specific",
        "YAML parse error",
        "schema validation",
        "missing file",
        "unsafe path",
        "duplicate task id",
        "Git ref",
        "side-effect-free",
        "no workspace",
        "no agent run",
        "no validation command",
        "no network call",
        "repo.path",
        "agent.prompt_template",
        "variant",
        "overlay",
        "task id",
        "task.repo_ref",
    ]:
        assert term in text


def test_development_plan_links_config_diagnostics_spec() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")

    assert "docs/config-diagnostics.md" in text


def test_user_docs_describe_config_diagnostics_and_strict_rules() -> None:
    config_docs = _squash(Path("docs/configuration.md").read_text(encoding="utf-8"))
    task_docs = _squash(Path("docs/task-format.md").read_text(encoding="utf-8"))
    readme = _squash(Path("README.md").read_text(encoding="utf-8"))

    for term in [
        "field-specific",
        "context-eval.yaml: repo.path",
        "tasks.yaml: tasks[task-1].validation.timeout_seconds",
        "filename-safe task IDs",
        "does not run agents, validation commands, or workspace setup",
    ]:
        assert term in config_docs

    for term in [
        "filename-safe",
        "letters, numbers, `.`, `_`, or `-`",
        "strict validation",
        "task.repo_ref",
    ]:
        assert term in task_docs

    for term in [
        "context-eval validate-config --strict --config examples/basic/context-eval.yaml",
        "field-specific diagnostics",
        "strict mode",
        "filename-safe task IDs",
    ]:
        assert term in readme
