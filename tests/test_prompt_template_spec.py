from pathlib import Path


def test_adapter_docs_describe_prompt_template_contract() -> None:
    text = Path("docs/adapter-api.md").read_text(encoding="utf-8")

    for term in [
        "## Prompt Templates",
        "prompt_template",
        "local file path",
        "resolved relative to the config file",
        "`{task_id}`",
        "`{task_title}`",
        "`{task_prompt}`",
        "`{variant}`",
        "`{repo_ref}`",
        "`{category}`",
        "`{difficulty}`",
        "missing prompt template file",
        "unknown template variable",
        "before the agent command runs",
        "built-in prompt remains unchanged",
    ]:
        assert term in text
