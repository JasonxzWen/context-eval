import pytest

from context_eval.adapters.command import render_command_template
from context_eval.models import TaskConfig
from context_eval.prompt import render_prompt


def test_command_template_variable_replacement() -> None:
    command = render_command_template(
        "myAgent --workspace {workspace} -p {prompt_file} --task {task_id} --variant {variant}",
        {
            "workspace": "/repo/work",
            "prompt": "Fix it",
            "prompt_file": "/tmp/prompt.md",
            "task_id": "bug-1",
            "variant": "experiment",
            "output_dir": "/tmp/out",
        },
    )

    assert command == (
        "myAgent --workspace /repo/work -p /tmp/prompt.md --task bug-1 --variant experiment"
    )


def test_prompt_contains_task_prompt_and_no_commit_instruction() -> None:
    task = TaskConfig(id="bug-1", title="Bug fix", prompt="Fix the cache invalidation bug.")

    prompt = render_prompt(task, "baseline")

    assert "Fix the cache invalidation bug." in prompt
    assert "Do not commit changes." in prompt
    assert "Context Variant: baseline" in prompt


def test_prompt_template_renders_task_variables(tmp_path) -> None:
    template = tmp_path / "prompt.md"
    template.write_text(
        "\n".join(
            [
                "Task={task_id}",
                "Title={task_title}",
                "Prompt={task_prompt}",
                "Variant={variant}",
                "Ref={repo_ref}",
                "Category={category}",
                "Difficulty={difficulty}",
            ]
        ),
        encoding="utf-8",
    )
    task = TaskConfig(
        id="bug-1",
        title="Bug fix",
        prompt="Fix the cache invalidation bug.\n",
        repo_ref="feature/ref",
        category="runtime",
        difficulty="medium",
    )

    prompt = render_prompt(task, "experiment", prompt_template=template, repo_ref="feature/ref")

    assert prompt == (
        "Task=bug-1\n"
        "Title=Bug fix\n"
        "Prompt=Fix the cache invalidation bug.\n"
        "Variant=experiment\n"
        "Ref=feature/ref\n"
        "Category=runtime\n"
        "Difficulty=medium"
    )


def test_prompt_template_rejects_unknown_variables(tmp_path) -> None:
    template = tmp_path / "prompt.md"
    template.write_text("Unknown={missing}", encoding="utf-8")
    task = TaskConfig(id="bug-1", prompt="Fix it.")

    with pytest.raises(ValueError, match="prompt template references unknown variable: missing"):
        render_prompt(task, "baseline", prompt_template=template, repo_ref="HEAD")
