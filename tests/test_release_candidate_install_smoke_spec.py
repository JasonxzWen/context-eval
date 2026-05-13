from pathlib import Path


def test_release_candidate_install_smoke_spec_documents_contract() -> None:
    text = Path("docs/release-candidate-install-smoke.md").read_text(encoding="utf-8")

    for term in [
        "built local wheel",
        "fixture repository",
        "fake local agent",
        "temporary config files",
        "context-eval validate-config",
        "context-eval run",
        "context-eval report",
        "context-eval export",
        "context-eval ui",
        "context-eval-app",
        "--no-browser --port 0 --check-startup",
        "do not contain hosted network call patterns",
        "manual publish checkpoint",
    ]:
        assert term in text


def test_development_plan_lists_capability_g_release_candidate_install_smoke() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")

    for term in [
        "Capability Epic G: Release Candidate Install Smoke And Changelog Finalization",
        "clean archive",
        "built package artifacts",
        "local fixture repository",
        "fake local agent",
        "manual publish checkpoint",
        "US-G1",
        "US-G5",
    ]:
        assert term in text
