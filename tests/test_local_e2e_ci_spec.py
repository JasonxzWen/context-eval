from pathlib import Path


def test_local_e2e_ci_spec_defines_ci_smoke_contract() -> None:
    text = Path("docs/local-e2e-ci.md").read_text(encoding="utf-8")

    for heading in [
        "# Local E2E CI Smoke And Test Taxonomy",
        "## Goal",
        "## Test Taxonomy",
        "## Local E2E Smoke Contract",
        "## CI Contract",
        "## Non-Goals",
        "## Acceptance Criteria",
    ]:
        assert heading in text

    for term in [
        "installed CLI",
        "fixture repository",
        "fake local agent",
        "context-eval run",
        "context-eval report",
        "context-eval export",
        "context-eval ui",
        "results.jsonl",
        "run_manifest.json",
        "report.md",
        "summary.csv",
        "summary.json",
        "context-eval-ui.html",
        "no hosted services",
        "no real external coding agent",
    ]:
        assert term in text


def test_local_e2e_ci_spec_preserves_product_boundaries() -> None:
    text = Path("docs/local-e2e-ci.md").read_text(encoding="utf-8")

    for term in [
        "local artifact-based",
        "not a benchmark or leaderboard",
        "must not call network services",
        "must not install or run a real external agent",
        "must not require browser automation in the default PR gate",
        "Playwright",
        "optional follow-up",
    ]:
        assert term in text


def test_local_e2e_ci_spec_selects_separate_ci_job_boundary() -> None:
    text = Path("docs/local-e2e-ci.md").read_text(encoding="utf-8")

    for term in [
        "separate `local-e2e` job",
        "one Python version and one OS",
        "`local_e2e` pytest marker",
        "excluded from the default pytest matrix",
        "python -m pytest tests/test_local_e2e_smoke.py -m local_e2e",
    ]:
        assert term in text
