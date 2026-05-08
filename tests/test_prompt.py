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
