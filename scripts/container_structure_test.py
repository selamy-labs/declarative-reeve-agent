#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT / "image" / "container-structure-test.yaml"
DEFAULT_LAYOUT = ROOT / "generated" / "image-layout"


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open() as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a YAML object")
    return data


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def container_path(rootfs: Path, path: str) -> Path:
    if not path.startswith("/"):
        raise ValueError(f"container path must be absolute: {path}")
    if ".." in Path(path).parts:
        raise ValueError(f"container path must not contain '..': {path}")
    return rootfs / path.lstrip("/")


def translate_path_arg(rootfs: Path, arg: str) -> str:
    if arg.startswith("/"):
        return str(container_path(rootfs, arg))
    return arg


def translate_env_value(rootfs: Path, value: str) -> str:
    parts = value.split(":")
    translated = [translate_path_arg(rootfs, part) if part.startswith("/") else part for part in parts]
    return ":".join(translated)


def assert_regexes(name: str, text: str, patterns: list[str], failures: list[str], invert: bool = False) -> int:
    checks = 0
    for pattern in patterns:
        checks += 1
        found = re.search(pattern, text, flags=re.MULTILINE) is not None
        if found == invert:
            verb = "matched forbidden" if invert else "did not match"
            failures.append(f"{name}: {verb} pattern {pattern!r}")
    return checks


def parse_env_list(env: list[str] | None) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in env or []:
        if "=" in item:
            key, value = item.split("=", 1)
            parsed[key] = value
    return parsed


def runtime_rootfs(image: str, runtime: str) -> tuple[tempfile.TemporaryDirectory[str], Path, dict[str, Any]]:
    if not shutil.which(runtime):
        raise SystemExit(f"{runtime} is required for --image mode")
    inspect = subprocess.run(
        [runtime, "image", "inspect", image],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    image_info = json.loads(inspect.stdout)[0]
    config = image_info.get("Config", {})
    labels = config.get("Labels") or {}
    metadata = {
        "baseImage": labels.get("dev.selamy.base-image"),
        "workdir": config.get("WorkingDir") or "/",
        "entrypoint": config.get("Entrypoint") or [],
        "cmd": config.get("Cmd") or [],
        "env": parse_env_list(config.get("Env")),
        "labels": labels,
    }

    tmp = tempfile.TemporaryDirectory()
    rootfs = (Path(tmp.name) / "rootfs").resolve()
    rootfs.mkdir()
    container = subprocess.check_output([runtime, "create", image], text=True).strip()
    try:
        archive = Path(tmp.name) / "rootfs.tar"
        with archive.open("wb") as handle:
            subprocess.run([runtime, "export", container], check=True, stdout=handle)
        with tarfile.open(archive) as tar:
            safe_extract(tar, rootfs)
    finally:
        subprocess.run([runtime, "rm", "-f", container], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return tmp, rootfs, metadata


def safe_extract(tar: tarfile.TarFile, destination: Path) -> None:
    dest = destination.resolve()
    for member in tar.getmembers():
        target = (destination / member.name).resolve()
        if not str(target).startswith(str(dest)):
            raise SystemExit(f"unsafe tar member path: {member.name}")
    tar.extractall(destination)


def load_layout(layout_dir: Path) -> tuple[None, Path, dict[str, Any]]:
    rootfs = (layout_dir / "rootfs").resolve()
    config = load_json(layout_dir / "image-config.json")
    if not rootfs.exists():
        raise SystemExit(f"layout rootfs missing: {rootfs}")
    return None, rootfs, config


def run_metadata_tests(spec: dict[str, Any], config: dict[str, Any], failures: list[str]) -> int:
    meta = spec.get("metadataTest", {})
    checks = 0
    scalar_fields = {
        "baseImage": config.get("baseImage"),
        "workdir": config.get("workdir"),
    }
    for key, actual in scalar_fields.items():
        if key in meta:
            checks += 1
            if actual != meta[key]:
                failures.append(f"metadata.{key}: expected {meta[key]!r}, got {actual!r}")
    for key in ["entrypoint", "cmd"]:
        if key in meta:
            checks += 1
            if list(config.get(key) or []) != list(meta[key]):
                failures.append(f"metadata.{key}: expected {meta[key]!r}, got {config.get(key)!r}")
    env = config.get("env") or {}
    for item in meta.get("env", []):
        checks += 1
        if env.get(item["key"]) != item["value"]:
            failures.append(f"metadata.env.{item['key']}: expected {item['value']!r}, got {env.get(item['key'])!r}")
    labels = config.get("labels") or {}
    for item in meta.get("labels", []):
        checks += 1
        if labels.get(item["key"]) != item["value"]:
            failures.append(f"metadata.labels.{item['key']}: expected {item['value']!r}, got {labels.get(item['key'])!r}")
    return checks


def run_file_tests(spec: dict[str, Any], rootfs: Path, failures: list[str]) -> int:
    checks = 0
    for item in spec.get("fileExistenceTests", []):
        checks += 1
        path = container_path(rootfs, item["path"])
        should_exist = bool(item.get("shouldExist", True))
        if path.exists() != should_exist:
            failures.append(f"{item['name']}: {item['path']} existence expected {should_exist}")
        if should_exist and "permissions" in item and path.exists():
            actual = path.stat().st_mode & 0o777
            expected = int(str(item["permissions"]), 8)
            checks += 1
            if actual != expected:
                failures.append(f"{item['name']}: permissions expected {oct(expected)}, got {oct(actual)}")
    for item in spec.get("fileContentTests", []):
        path = container_path(rootfs, item["path"])
        if not path.exists():
            failures.append(f"{item['name']}: {item['path']} missing")
            continue
        text = path.read_text(errors="replace")
        checks += assert_regexes(item["name"], text, item.get("expectedContents", []), failures)
        checks += assert_regexes(item["name"], text, item.get("excludedContents", []), failures, invert=True)
    for item in spec.get("forbiddenPathTests", []):
        checks += 1
        path = container_path(rootfs, item["path"])
        if path.exists():
            failures.append(f"{item['name']}: forbidden path exists at {item['path']}")
    return checks


def run_layout_command_test(
    item: dict[str, Any],
    rootfs: Path,
    config: dict[str, Any],
    failures: list[str],
) -> int:
    env = os.environ.copy()
    for key, value in (config.get("env") or {}).items():
        env[key] = translate_env_value(rootfs, str(value))
    args = [translate_path_arg(rootfs, str(arg)) for arg in item.get("args", [])]
    workdir = container_path(rootfs, config.get("workdir") or "/")
    workdir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [item["command"], *args],
        cwd=workdir,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return check_command_result(item, result.returncode, result.stdout + result.stderr, failures)


def run_image_command_test(item: dict[str, Any], image: str, runtime: str, failures: list[str]) -> int:
    command = [runtime, "run", "--rm", "--entrypoint", item["command"], image, *[str(arg) for arg in item.get("args", [])]]
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return check_command_result(item, result.returncode, result.stdout + result.stderr, failures)


def check_command_result(item: dict[str, Any], code: int, output: str, failures: list[str]) -> int:
    checks = 1
    expected_code = int(item.get("expectedExitCode", 0))
    if code != expected_code:
        failures.append(f"{item['name']}: exit code expected {expected_code}, got {code}; output:\n{output}")
    checks += assert_regexes(item["name"], output, item.get("expectedOutput", []), failures)
    checks += assert_regexes(item["name"], output, item.get("excludedOutput", []), failures, invert=True)
    return checks


def run_command_tests(
    spec: dict[str, Any],
    rootfs: Path,
    config: dict[str, Any],
    failures: list[str],
    image: str | None,
    runtime: str,
) -> int:
    checks = 0
    for item in spec.get("commandTests", []):
        if image:
            checks += run_image_command_test(item, image, runtime, failures)
        else:
            checks += run_layout_command_test(item, rootfs, config, failures)
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--layout", default=str(DEFAULT_LAYOUT))
    source.add_argument("--image")
    parser.add_argument("--spec", default=str(DEFAULT_SPEC))
    parser.add_argument("--runtime", default="docker")
    parser.add_argument("--docker", dest="runtime", default=argparse.SUPPRESS)
    args = parser.parse_args()

    spec = load_yaml(Path(args.spec))
    tmp: tempfile.TemporaryDirectory[str] | None = None
    if args.image:
        tmp, rootfs, config = runtime_rootfs(args.image, args.runtime)
    else:
        _, rootfs, config = load_layout(Path(args.layout))

    failures: list[str] = []
    checks = 0
    try:
        checks += run_metadata_tests(spec, config, failures)
        checks += run_file_tests(spec, rootfs, failures)
        checks += run_command_tests(spec, rootfs, config, failures, args.image, args.runtime)
    finally:
        if tmp:
            tmp.cleanup()

    if failures:
        print("\n".join(f"CONTAINER STRUCTURE ERROR: {failure}" for failure in failures))
        return 1
    print(f"container structure tests ok ({checks} checks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
