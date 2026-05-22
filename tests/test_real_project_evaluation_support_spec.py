from pathlib import Path


def _squash(text: str) -> str:
    return " ".join(text.split())


def test_real_project_evaluation_plan_documents_required_contract() -> None:
    text = _squash(Path(
        "docs/plans/2026-05-21-real-project-evaluation-support.md"
    ).read_text(encoding="utf-8"))

    for term in [
        "private production repositories",
        "old `AGENTS.md`",
        "newer `AGENTS.md` plus project wiki docs",
        "compile_diagnosis",
        "bugfix",
        "incident",
        "feature",
        "reference_evidence",
        "not sending it to the coding agent by default",
        "Codex telemetry must come from structured local run artifacts",
        "Missing telemetry remains `null`",
        "default same-agent local AI arbitration runner support",
        "no hidden hosted judge calls",
        "AI arbitration runner output is saved as local soft evidence",
    ]:
        assert term in text


def test_task_format_documents_real_project_fields() -> None:
    text = _squash(Path("docs/task-format.md").read_text(encoding="utf-8"))

    for term in [
        'case_type: "bugfix"',
        "reference_evidence:",
        "`compile_diagnosis`",
        "`incident`",
        "`feature`",
        "It is not appended to the coding-agent prompt by default",
        "`fix_ref`",
    ]:
        assert term in text


def test_development_plan_tracks_real_project_capability() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")

    for term in [
        "PR M: Real Project Evaluation Support",
        "Current follow-up capability: `real-project-evaluation-support`",
        "## Capability Epic M: Real Project Evaluation Support",
        "per-case starting version",
        "reference_evidence",
        "Do not make hidden OpenAI, Claude, or other hosted LLM judge calls",
        "Do not infer token or tool metrics from unstructured logs",
        "Run AI arbitration by default with the same local executor",
    ]:
        assert term in text
