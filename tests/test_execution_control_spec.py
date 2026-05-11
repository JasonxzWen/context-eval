from pathlib import Path


def test_evaluation_docs_describe_bounded_parallelism_contract() -> None:
    text = Path("docs/evaluation.md").read_text(encoding="utf-8")

    for term in [
        "## Bounded Parallelism",
        "--jobs N",
        "defaults to 1",
        "at least 1",
        "single-threaded",
        "results.jsonl",
        "planned task, variant, and trial order",
        "prompt, log, patch, artifact, and workspace paths",
        "local run artifacts",
    ]:
        assert term in text


def test_development_plan_includes_bounded_parallelism_acceptance_terms() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")

    assert "--jobs N" in text
    assert "result writing through a single append-safe writer" in text
    assert "Parallel and serial runs produce equivalent result sets" in text
