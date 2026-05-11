from pathlib import Path


def _squash(text: str) -> str:
    return " ".join(text.split())


def test_configuration_docs_define_validation_timeout_defaults_contract() -> None:
    text = _squash(Path("docs/configuration.md").read_text(encoding="utf-8"))

    for term in [
        "evaluation.timeout_seconds",
        "task.validation.timeout_seconds",
        "Validation command timeout resolution",
        "task-level timeout overrides the config-level default",
        "If neither field is set, validation commands run without a timeout",
        "positive integer number of seconds",
    ]:
        assert term in text


def test_evaluation_docs_define_validation_timeout_behavior() -> None:
    text = Path("docs/evaluation.md").read_text(encoding="utf-8")

    for term in [
        "## Validation Timeouts",
        "`task.validation.timeout_seconds`",
        "`config.evaluation.timeout_seconds`",
        "A timed-out validation command records `timeout=true`",
        "`exit_code=null`",
        "`validation_status=\"failed\"`",
        "`status=\"validation_failed\"`",
    ]:
        assert term in text


def test_development_plan_marks_validation_timeout_contract_as_current_work() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")

    for term in [
        "Validation command timeout defaults are now the active Phase 2 story",
        "document timeout resolution before runtime changes",
        "config-level and task-level validation command timeout defaults",
    ]:
        assert term in text
