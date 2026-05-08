from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) > 1:
        Path(sys.argv[1]).read_text(encoding="utf-8")

    target = Path("fixture_app/greetings.py")
    text = target.read_text(encoding="utf-8")
    old = 'return f"Hello, {name}"'
    new = 'return f"Hello, {name}!"'

    if new in text:
        return
    if old not in text:
        raise SystemExit("expected greeting implementation was not found")

    target.write_text(text.replace(old, new), encoding="utf-8")


if __name__ == "__main__":
    main()
