from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from career_steward.reconciler import reconcile
from career_steward.validator import load_yaml, validate_repo


class ManifestContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load_yaml(ROOT / "agent.manifest.yaml")

    def test_manifest_contract_runtime(self) -> None:
        runtime = self.manifest["runtime"]
        self.assertEqual(runtime["engine"], "hermes-agent")
        self.assertEqual(runtime["image"]["repository"], "nousresearch/hermes-agent")
        self.assertEqual(runtime["image"]["tag"], "main")
        self.assertEqual(runtime["image"]["tagPolicy"], "pinned-digest")
        self.assertIn("/opt/data/**", runtime["state"]["mutableZones"])
        self.assertIn("/etc/hermes/**", runtime["state"]["immutableZones"])

    def test_secret_references_are_declared_not_values(self) -> None:
        required = load_yaml(ROOT / "contracts" / "required-secrets.yaml")
        ids = {item["id"] for item in required["secrets"]}
        self.assertIn("openrouter-api-key", ids)
        for item in required["secrets"]:
            self.assertIn("remoteKey", item)
            self.assertIn("injectAs", item)
            self.assertIn("verifies", item)
            self.assertNotIn("value", item)

    def test_feature_flags_declared(self) -> None:
        flags = self.manifest["featureFlags"]["flags"]
        self.assertIn("career-steward.ops.career-email-check-enabled", flags)
        self.assertIn("career-steward.ops.whatsapp-intake-enabled", flags)
        self.assertEqual(flags["fleet.verbosity"]["default"], "normal")

    def test_oci_contract_lists_bundled_skills(self) -> None:
        out = ROOT / "generated" / "test-contract"
        rendered = reconcile(ROOT, out)
        image = json.loads(rendered["image_manifest"].read_text())
        self.assertEqual(image["runtimeBaseImage"], "nousresearch/hermes-agent:main")
        self.assertEqual(image["tagPolicy"], "pinned-digest")
        self.assertIn("bundled skill specs", image["contains"])
        self.assertIn("real user credentials", image["doesNotContain"])

    def test_skill_bundle_declares_ability_sources(self) -> None:
        skills = self.manifest["skills"]["refs"]
        names = {item["name"] for item in skills}
        provides = {capability for item in skills for capability in item["provides"]}
        self.assertIn("career-opportunity-triage", names)
        self.assertIn("approval-gated-correspondence", names)
        self.assertIn("career-email-triage", provides)
        self.assertIn("approval-gated-reply-drafting", provides)

    def test_telegram_connector_declared(self) -> None:
        telegram = self.manifest["capabilities"]["connectors"]["telegram"]
        self.assertTrue(telegram["enabled"])
        self.assertIn("notify-user", telegram["capabilities"])

    def test_google_workspace_connector_declared(self) -> None:
        google = self.manifest["capabilities"]["connectors"]["googleWorkspace"]
        self.assertTrue(google["enabled"])
        self.assertIn("gmail.read", google["capabilities"])
        self.assertIn("calendar.read", google["capabilities"])

    def test_state_maintenance_schedules_declared(self) -> None:
        schedules = self.manifest["schedules"]
        self.assertEqual(schedules["stateRetention"]["workflow"], "state-maintenance")
        self.assertEqual(schedules["pvcPruning"]["workflow"], "state-maintenance")

    def test_verify_contract_has_quality_gates(self) -> None:
        result = validate_repo(ROOT)
        self.assertEqual(result["status"], "ok")
        self.assertIn("schema-valid", result["checks"])


if __name__ == "__main__":
    unittest.main()
