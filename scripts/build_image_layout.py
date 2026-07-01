#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LAYOUT = ROOT / "image" / "image-layout.yaml"
DEFAULT_OUT = ROOT / "generated" / "image-layout"
IGNORED_NAMES = {"__pycache__", ".DS_Store", ".pytest_cache"}


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a YAML object")
    return data


def require_container_path(path: str) -> None:
    if not path.startswith("/"):
        raise SystemExit(f"container path must be absolute: {path}")
    if ".." in Path(path).parts:
        raise SystemExit(f"container path must not contain '..': {path}")


def rootfs_path(rootfs: Path, container_path: str) -> Path:
    require_container_path(container_path)
    return rootfs / container_path.lstrip("/")


def ignore_names(_: str, names: list[str]) -> set[str]:
    return {name for name in names if name in IGNORED_NAMES or name.endswith((".pyc", ".pyo"))}


def copy_entry(source_root: Path, rootfs: Path, entry: dict[str, str]) -> dict[str, str]:
    source = source_root / entry["source"]
    target = rootfs_path(rootfs, entry["target"])
    if not source.exists():
        raise SystemExit(f"image layout source missing: {entry['source']}")
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target, ignore=ignore_names, dirs_exist_ok=True)
    else:
        shutil.copy2(source, target)
    return {"source": entry["source"], "target": entry["target"]}


def build_layout(layout_path: Path, out_dir: Path) -> dict[str, Any]:
    layout = load_yaml(layout_path)
    if layout.get("kind") != "ReferenceImageLayout":
        raise SystemExit("image layout kind must be ReferenceImageLayout")

    rootfs = out_dir / "rootfs"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    rootfs.mkdir(parents=True)

    copied = [copy_entry(ROOT, rootfs, entry) for entry in layout.get("copies", [])]
    base = layout["baseImage"]
    config = {
        "name": layout["metadata"]["name"],
        "baseImage": f"{base['repository']}:{base['tag']}",
        "tagPolicy": base["tagPolicy"],
        "workdir": layout["workdir"],
        "entrypoint": layout["entrypoint"],
        "cmd": layout["cmd"],
        "env": layout.get("env", {}),
        "labels": layout.get("labels", {}),
        "copied": copied,
        "forbiddenPaths": layout.get("forbiddenPaths", []),
    }
    (out_dir / "image-config.json").write_text(json.dumps(config, indent=2, sort_keys=True) + "\n")
    return config


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", default=str(DEFAULT_LAYOUT))
    parser.add_argument("--out", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    config = build_layout(Path(args.layout), Path(args.out))
    print(json.dumps({"status": "ok", "baseImage": config["baseImage"], "out": args.out}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
