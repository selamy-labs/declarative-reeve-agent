from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .yamlutil import dump_yaml, load_yaml


def _connector_env(manifest: dict[str, Any]) -> dict[str, str]:
    connectors = manifest.get("capabilities", {}).get("connectors", {})
    env: dict[str, str] = {}
    for name, connector in connectors.items():
        if not isinstance(connector, dict) or not connector.get("enabled", False):
            continue
        env[f"CONNECTOR_{name.upper()}_ENABLED"] = "true"
    return env


def render_runtime_config(manifest: dict[str, Any]) -> dict[str, Any]:
    runtime = manifest["runtime"]
    return {
        "agent": {
            "name": manifest["metadata"]["name"],
            "display_name": manifest["identity"]["displayName"],
            "mandate": manifest["identity"]["mandate"],
        },
        "model": runtime["model"],
        "toolsets": manifest["capabilities"].get("toolsets", []),
        "skills": manifest.get("skills", {}),
        "knowledge": manifest["knowledge"],
        "featureFlags": manifest.get("featureFlags", {}),
        "env": _connector_env(manifest),
    }


def render_helm_values(manifest: dict[str, Any]) -> dict[str, Any]:
    runtime = manifest["runtime"]
    state = runtime["state"]["pvc"]
    return {
        "agent": {
            "name": manifest["metadata"]["name"],
            "identity": manifest["identity"]["displayName"],
            "role": manifest["identity"]["role"],
            "mandate": manifest["identity"]["mandate"],
        },
        "image": runtime["image"],
        "resources": runtime["resources"],
        "storage": {
            "class": state["storageClass"],
            "size": state["size"],
        },
        "schedules": manifest["schedules"],
        "openFeature": manifest.get("featureFlags", {}),
    }


def render_external_secrets(required: dict[str, Any]) -> dict[str, Any]:
    items = []
    for secret in required.get("secrets", []):
        inject = secret.get("injectAs", {})
        items.append(
            {
                "id": secret["id"],
                "provider": secret["provider"],
                "remoteKey": secret["remoteKey"],
                "requiredFor": secret["requiredFor"],
                "injectAs": inject,
                "verification": secret.get("verifies", {}),
            }
        )
    return {"apiVersion": "agents.selamy.dev/v1alpha1", "kind": "RenderedSecretRefs", "secrets": items}


def render_schedules(manifest: dict[str, Any]) -> dict[str, Any]:
    return {
        "apiVersion": "agents.selamy.dev/v1alpha1",
        "kind": "RenderedSchedules",
        "schedules": manifest["schedules"],
    }


def render_image_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    image = manifest["runtime"]["image"]
    return {
        "imageContractVersion": manifest["apiVersion"],
        "runtimeBaseImage": f"{image['repository']}:{image['tag']}",
        "tagPolicy": image["tagPolicy"],
        "contains": [
            "hermes-compatible runtime entrypoint",
            "career_steward reference reconciler",
            "workflow manifests",
            "bundled skill specs",
            "policy manifests",
            "schema validators",
            "sim-mode fixtures",
        ],
        "doesNotContain": [
            "real user credentials",
            "source operator private tracker data",
            "live OAuth tokens",
            "deployment environment ownership",
        ],
    }


def reconcile(root: Path, out_dir: Path) -> dict[str, Path]:
    manifest = load_yaml(root / "agent.manifest.yaml")
    required = load_yaml(root / "contracts" / "required-secrets.yaml")
    out_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "runtime_config": out_dir / "runtime-config.yaml",
        "helm_values": out_dir / "helm-values.yaml",
        "external_secrets": out_dir / "external-secrets.yaml",
        "schedules": out_dir / "schedules.yaml",
        "image_manifest": out_dir / "image-manifest.json",
    }
    dump_yaml(render_runtime_config(manifest), outputs["runtime_config"])
    dump_yaml(render_helm_values(manifest), outputs["helm_values"])
    dump_yaml(render_external_secrets(required), outputs["external_secrets"])
    dump_yaml(render_schedules(manifest), outputs["schedules"])
    outputs["image_manifest"].write_text(json.dumps(render_image_manifest(manifest), indent=2, sort_keys=True) + "\n")
    return outputs
