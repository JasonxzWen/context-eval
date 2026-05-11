from pathlib import Path


def test_development_plan_defines_reconciliation_status_model() -> None:
    text = Path("docs/development-plan.md").read_text(encoding="utf-8")

    for term in [
        "## Plan Status Model",
        "`complete for current scope`",
        "`mostly complete`",
        "`planned next`",
        "`deferred`",
        "A status line must separate shipped behavior from remaining backlog",
    ]:
        assert term in text
