#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {".git", "generated", "__pycache__", ".pytest_cache"}
MARKERS = [
    "Pat" + "rick",
    "pse" + "lamy",
    "selamy" + "-core",
    "/Users/" + "pse" + "lamy",
    "/home/" + "pse" + "lamy",
    "access" + "_token",
    "refresh" + "_token",
    "api" + "_hash",
    "private" + "_key",
    "TO" + "DO",
    "TB" + "D",
    "FIX" + "ME",
    "Ree" + "ve",
    "ree" + "ve",
    "declarative-" + "ree" + "ve-agent",
    "selamy-labs/" + "hermes-agent",
]


def should_skip(path: Path) -> bool:
    parts = set(path.relative_to(ROOT).parts)
    return bool(parts & EXCLUDED_DIRS)


def main() -> int:
    hits: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or should_skip(path):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_no, line in enumerate(text.splitlines(), 1):
            for marker in MARKERS:
                if marker in line:
                    hits.append(f"{path.relative_to(ROOT)}:{line_no}: marker {marker!r}")
    if hits:
        print("\n".join(hits))
        return 1
    print("private marker scan ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
