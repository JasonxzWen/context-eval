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


def test_readme_documents_bounded_parallel_run_usage() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    for term in [
        "context-eval run --config examples/basic/context-eval.yaml --jobs 2",
        "`--jobs` defaults to 1",
        "concurrent local cases",
        "local run artifacts",
        "not an agent leaderboard",
    ]:
        assert term in text


def test_evaluation_docs_describe_cleanup_policy_contract() -> None:
    text = Path("docs/evaluation.md").read_text(encoding="utf-8")

    for term in [
        "## Cleanup Policies",
        "--cleanup-policy",
        "`never`",
        "`always`",
        "`successful`",
        "`failed`",
        "default cleanup policy is `never`",
        "`--cleanup` remains shorthand for `--cleanup-policy always`",
        "cleanup_status",
        "`skipped` when the selected policy keeps the workspace",
        "workspace_retained",
    ]:
        assert term in text


def test_readme_documents_cleanup_policy_usage() -> None:
    text = Path("README.md").read_text(encoding="utf-8")

    for term in [
        "context-eval run --config examples/basic/context-eval.yaml --cleanup-policy successful",
        "`--cleanup-policy`",
        "`never`",
        "`always`",
        "`successful`",
        "`failed`",
        "`--cleanup` is shorthand for `--cleanup-policy always`",
        "local run artifacts",
    ]:
        assert term in text


def test_evaluation_docs_describe_run_manifest_contract() -> None:
    text = Path("docs/evaluation.md").read_text(encoding="utf-8")

    for term in [
        "## Run Manifest",
        "run_manifest.json",
        "selected tasks",
        "selected variants",
        "trials",
        "case_matrix",
        "config_hash",
        "task_hash",
        "variant_hash",
        "planned task, variant, and trial order",
        "local run artifact",
        "does not rerun agents",
    ]:
        assert term in text
