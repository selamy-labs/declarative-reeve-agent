from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .yamlutil import load_yaml, yaml


SECRET_VALUE_KEYS = re.compile(r"(value|token|password|secret|privateKey|apiKey)$", re.IGNORECASE)
REQUIRED_CHECKS = {
    "schema-valid",
    "secrets-declared-not-committed",
    "approval-gates-present",
    "external-side-effects-gated",
    "private-data-redaction",
    "immutable-runtime-boundary",
    "generated-kubernetes-renders",
}
SKILL_REF = re.compile(r"^skills/[a-z0-9-]+/SKILL\.md$")


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _walk_secret_values(obj: Any, path: str, errors: list[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            next_path = f"{path}.{key}" if path else str(key)
            if SECRET_VALUE_KEYS.search(str(key)) and key not in {"remoteKey", "secretKey", "secretName", "apiKeySecretRef", "baseUrlSecretRef"}:
                if isinstance(value, str) and value and not value.startswith("optional-"):
                    errors.append(f"secret-like literal field is not allowed at {next_path}")
            _walk_secret_values(value, next_path, errors)
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            _walk_secret_values(value, f"{path}[{idx}]", errors)


def validate_manifest(manifest: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    _require(manifest.get("kind") == "DeclarativeAgent", "manifest kind must be DeclarativeAgent", errors)
    _require(str(manifest.get("apiVersion", "")).startswith("agents.selamy.dev/v1"), "manifest apiVersion must be v1", errors)
    _require("x-versioning" in manifest, "manifest must declare x-versioning rules", errors)
    checks = set(manifest.get("validation", {}).get("requiredChecks", []))
    _require(REQUIRED_CHECKS.issubset(checks), "manifest missing required validation checks", errors)
    mutable = manifest.get("runtime", {}).get("state", {}).get("mutableZones", [])
    immutable = manifest.get("runtime", {}).get("state", {}).get("immutableZones", [])
    _require("/opt/data/**" in mutable, "manifest must declare /opt/data/** mutable zone", errors)
    _require("/etc/hermes/**" in immutable, "manifest must declare /etc/hermes/** immutable zone", errors)
    workflow_names = set()
    workflow_refs = set()
    workflow_capabilities = set()
    for item in manifest.get("workflows", []):
        ref = item.get("ref")
        path = root / str(ref)
        _require(path.exists(), f"workflow ref missing: {ref}", errors)
        workflow_refs.add(str(ref))
        if path.exists():
            workflow = load_yaml(path)
            workflow_names.add(workflow["metadata"]["name"])
            workflow_capabilities.update(workflow.get("capabilities", []))
    for name, schedule in manifest.get("schedules", {}).items():
        _require(schedule.get("workflow") in workflow_names, f"schedule {name} references unknown workflow", errors)
    errors.extend(validate_skills(manifest, root, workflow_refs, workflow_capabilities))
    _walk_secret_values(manifest, "manifest", errors)
    return errors


def _load_skill_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text()
    if not text.startswith("---\n"):
        raise ValueError("skill must start with YAML frontmatter")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("skill frontmatter must be closed")
    data = yaml.safe_load(parts[1]) or {}
    if not isinstance(data, dict):
        raise ValueError("skill frontmatter must be a mapping")
    return data


def validate_skills(manifest: dict[str, Any], root: Path, workflow_refs: set[str], workflow_capabilities: set[str]) -> list[str]:
    errors: list[str] = []
    skills = manifest.get("skills", {})
    refs = skills.get("refs", []) if isinstance(skills, dict) else []
    bundle = skills.get("bundle", {}) if isinstance(skills, dict) else {}
    _require(bundle.get("mountPath") == "/etc/career-steward/skills", "skill bundle must mount at /etc/career-steward/skills", errors)
    _require(bundle.get("format") == "markdown-frontmatter", "skill bundle must use markdown-frontmatter format", errors)
    _require(refs, "manifest must declare bundled skill refs", errors)

    names: set[str] = set()
    provided: set[str] = set()
    for item in refs:
        name = str(item.get("name", ""))
        ref = str(item.get("ref", ""))
        _require(bool(name), "skill ref missing name", errors)
        _require(name not in names, f"duplicate skill name: {name}", errors)
        names.add(name)
        _require(SKILL_REF.match(ref) is not None, f"invalid skill ref: {ref}", errors)
        _require(item.get("audience") in {"worker", "universal"}, f"skill {name} has invalid audience", errors)
        _require(bool(item.get("provides")), f"skill {name} must declare provided capabilities", errors)
        _require(bool(item.get("requiredBy")), f"skill {name} must declare required workflows", errors)
        _require(set(item.get("requiredBy", [])).issubset(workflow_refs), f"skill {name} references unknown workflow", errors)
        provided.update(item.get("provides", []))
        path = root / ref
        _require(path.exists(), f"skill ref missing: {ref}", errors)
        if path.exists():
            try:
                frontmatter = _load_skill_frontmatter(path)
            except ValueError as exc:
                errors.append(f"skill {ref} invalid: {exc}")
                continue
            _require(frontmatter.get("name") == name, f"skill {ref} frontmatter name must be {name}", errors)
            _require(bool(frontmatter.get("description")), f"skill {name} missing description", errors)

    missing = sorted(workflow_capabilities - provided)
    _require(not missing, f"workflow capabilities missing skill coverage: {', '.join(missing)}", errors)
    return errors


def validate_secrets(root: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = load_yaml(root / "contracts" / "required-secrets.yaml")
    declared = {item["id"] for item in required.get("secrets", [])}
    _require(declared, "required secrets must not be empty", errors)
    for item in required.get("secrets", []):
        _require("remoteKey" in item, f"secret {item.get('id')} missing remoteKey", errors)
        _require("injectAs" in item, f"secret {item.get('id')} missing injectAs", errors)
        _require("verifies" in item, f"secret {item.get('id')} missing verification check", errors)
        _walk_secret_values(item, f"secret.{item.get('id')}", errors)
    connectors = manifest.get("capabilities", {}).get("connectors", {})
    for name, connector in connectors.items():
        for secret in connector.get("secrets", []) if isinstance(connector, dict) else []:
            _require(secret in declared, f"connector {name} references undeclared secret {secret}", errors)
    return errors


def validate_policy(root: Path) -> list[str]:
    errors: list[str] = []
    policy = load_yaml(root / "policies" / "approval-gates.yaml")
    side = policy.get("sideEffects", {})
    exact = set(side.get("requireExactApproval", []))
    forbidden = set(side.get("forbidden", []))
    _require(policy.get("default") == "deny-external-side-effects", "approval policy must default deny", errors)
    for action in ["send.email", "send.linkedin-message", "send.whatsapp-message", "create.calendar-event", "publish.public-post"]:
        _require(action in exact or action in forbidden, f"{action} must be gated or forbidden", errors)
    _require("commit.secret-value" in forbidden, "committing secrets must be forbidden", errors)
    shape = set(policy.get("approvalShape", {}).get("requiredFields", []))
    _require({"recipient", "channel", "exactTextOrArtifactUrl", "currentUserApproval"}.issubset(shape), "approval shape incomplete", errors)
    return errors


def validate_parity(root: Path) -> list[str]:
    errors: list[str] = []
    inventory = load_yaml(root / "docs" / "capability-parity-inventory.yaml")
    tests = set()
    for path in (root / "tests").glob("test_*.py"):
        tests.add(path.name)
    for item in inventory.get("capabilities", []):
        _require(item.get("currentCapability"), "parity row missing currentCapability", errors)
        _require(item.get("declarativeSurface"), f"parity row {item.get('id')} missing declarativeSurface", errors)
        _require(item.get("test"), f"parity row {item.get('id')} missing test", errors)
        if item.get("testFile"):
            _require(item["testFile"] in tests, f"parity row {item.get('id')} references missing {item['testFile']}", errors)
    return errors


def validate_docs(root: Path) -> list[str]:
    errors: list[str] = []
    required = [
        "docs/architecture.md",
        "docs/technical-spec-v1.md",
        "docs/reconciler-contract.md",
        "docs/oci-image-contents.md",
        "docs/policy-engine-spec.md",
        "docs/observability-contract.md",
        "docs/state-memory-migration.md",
        "docs/capability-parity-inventory.md",
        "docs/adr-001-vessel-and-distribution.md",
        "docs/adr-002-chart-boundary.md",
        "docs/adr-003-reconciler-ownership-and-drift.md",
        "docs/adr-004-state-migration.md",
        "docs/instantiate-new-person-sim.md",
    ]
    for rel in required:
        path = root / rel
        _require(path.exists(), f"required doc missing: {rel}", errors)
        if path.exists():
            text = path.read_text()
            markers = ["TB" + "D", "TO" + "DO"]
            _require(not any(marker in text for marker in markers), f"unfinished marker in {rel}", errors)
    return errors


def validate_repo(root: Path) -> dict[str, Any]:
    json.loads((root / "schemas" / "agent.manifest.schema.json").read_text())
    manifest = load_yaml(root / "agent.manifest.yaml")
    errors: list[str] = []
    errors.extend(validate_manifest(manifest, root))
    errors.extend(validate_secrets(root, manifest))
    errors.extend(validate_policy(root))
    errors.extend(validate_docs(root))
    if (root / "docs" / "capability-parity-inventory.yaml").exists():
        errors.extend(validate_parity(root))
    if errors:
        raise SystemExit("\n".join(f"VERIFY ERROR: {error}" for error in errors))
    return {"status": "ok", "checks": sorted(REQUIRED_CHECKS)}
