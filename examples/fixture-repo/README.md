# context-eval fixture repo

This is a tiny local target repository for the context-eval quickstart.

Run this once before using `examples/basic/context-eval.yaml`:

```bash
python examples/fixture-repo/setup_fixture_repo.py
```

The setup script initializes local Git history on branch `main`. The committed
fixture intentionally contains a small greeting bug so the example deterministic
agent can produce a patch and pass `python -m pytest`.
