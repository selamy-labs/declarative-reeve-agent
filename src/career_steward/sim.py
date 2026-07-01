from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .policy import privacy_errors
from .yamlutil import load_yaml


def classify(text: str) -> str:
    lower = text.lower()
    if any(token in lower for token in ["interview", "schedule", "calendar", "availability"]):
        return "scheduling"
    if any(token in lower for token in ["resume", "cv"]):
        return "resume-needed"
    if any(token in lower for token in ["not moving forward", "unfortunately"]):
        return "closure"
    return "reply-needed"


def draft_reply(inbound: dict[str, Any], classification: str) -> str:
    company = inbound["company"]
    role = inbound["role"]
    if classification == "scheduling":
        return (
            f"Hi {inbound['contact_name']}, thanks for reaching out. "
            f"{company} and the {role} role sound relevant. "
            "Could you share the interview format, level, compensation range, and working model? "
            "I am happy to find time once those details are clear."
        )
    return (
        f"Hi {inbound['contact_name']}, thanks for reaching out. "
        f"The {role} role at {company} sounds relevant. "
        "Could you send the role scope, level, compensation range, process, and working model?"
    )


def pipeline_row(inbound: dict[str, Any], classification: str, draft: str) -> dict[str, Any]:
    return {
        "company": inbound["company"],
        "contact": inbound["contact_name"],
        "role": inbound["role"],
        "source": inbound["source"],
        "classification": classification,
        "state": "qualification-needed" if classification in {"reply-needed", "scheduling"} else classification,
        "nextAction": "await-user-approval-for-draft",
        "draft": draft,
        "approvalRequired": True,
        "publicSafe": not privacy_errors(draft),
    }


def run_sim(manifest_path: Path, input_path: Path) -> dict[str, Any]:
    manifest = load_yaml(manifest_path)
    inbound = json.loads(input_path.read_text())
    classification = classify(inbound["message"])
    draft = draft_reply(inbound, classification)
    privacy = privacy_errors(draft)
    row = pipeline_row(inbound, classification, draft)
    return {
        "simMode": True,
        "agent": manifest["metadata"]["name"],
        "skillsLoaded": [item["name"] for item in manifest.get("skills", {}).get("refs", [])],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "steps": [
            {"name": "intake", "status": "ok", "source": inbound["source"]},
            {"name": "classify", "status": "ok", "classification": classification},
            {"name": "draft", "status": "ok", "text": draft},
            {"name": "approval_gate", "status": "blocked-pending-human-approval", "required": True},
            {"name": "pipeline_update", "status": "ok", "row": row},
            {"name": "privacy_validation", "status": "ok" if not privacy else "failed", "errors": privacy},
        ],
        "touchedRealAccounts": False,
        "externalSideEffects": [],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    result = run_sim(Path(args.manifest), Path(args.input))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    if result["steps"][-1]["status"] != "ok":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
