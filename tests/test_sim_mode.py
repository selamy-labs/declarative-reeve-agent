from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from career_steward.sim import run_sim


class SimModeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.result = run_sim(ROOT / "agent.manifest.yaml", ROOT / "examples" / "sim" / "inbound-message.json")

    def test_career_steward_loop_sim(self) -> None:
        self.assertTrue(self.result["simMode"])
        self.assertFalse(self.result["touchedRealAccounts"])
        self.assertEqual(self.result["externalSideEffects"], [])
        self.assertIn("career-opportunity-triage", self.result["skillsLoaded"])
        self.assertEqual([step["name"] for step in self.result["steps"]], [
            "intake",
            "classify",
            "draft",
            "approval_gate",
            "pipeline_update",
            "privacy_validation",
        ])

    def test_sim_updates_pipeline_row(self) -> None:
        update = next(step for step in self.result["steps"] if step["name"] == "pipeline_update")
        row = update["row"]
        self.assertEqual(row["company"], "Example Robotics")
        self.assertTrue(row["approvalRequired"])
        self.assertTrue(row["publicSafe"])


if __name__ == "__main__":
    unittest.main()
