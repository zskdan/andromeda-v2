import json
import tempfile
import unittest
from pathlib import Path

from scripts.check_change_impact import assess


class ChangeImpactRuleTests(unittest.TestCase):
    def setUp(self):
        self.rules = {
            "schema_version": 1,
            "rules": [
                {
                    "id": "mechanical",
                    "review_owner": "flight_dynamics",
                    "trigger_paths": ["mechanical/**"],
                    "acceptable_evidence_paths": ["simulation/**", "impact/**"],
                    "no_update_rule": "record evidence",
                },
                {
                    "id": "electronics",
                    "review_owner": "structures_mechanisms",
                    "trigger_paths": ["electronics/**"],
                    "acceptable_evidence_paths": ["mechanical/**", "impact/**"],
                    "no_update_rule": "record evidence",
                },
            ],
        }

    def assess_paths(self, paths):
        with tempfile.TemporaryDirectory() as directory:
            rules_path = Path(directory) / "rules.json"
            rules_path.write_text(json.dumps(self.rules), encoding="utf-8")
            return assess(paths, rules_path)

    def test_mechanical_change_requires_simulation_evidence(self):
        result = self.assess_paths(["mechanical/model.FCStd"])
        self.assertEqual("fail", result["overall_status"])

    def test_mechanical_change_accepts_simulation_update(self):
        result = self.assess_paths(
            ["mechanical/model.FCStd", "simulation/rocket.ork"]
        )
        self.assertEqual("pass", result["overall_status"])

    def test_electronics_change_requires_mechanical_evidence(self):
        result = self.assess_paths(["electronics/controller.kicad_pcb"])
        self.assertEqual("fail", result["overall_status"])

    def test_electronics_change_accepts_mechanical_review_record(self):
        result = self.assess_paths(
            ["electronics/controller.kicad_pcb", "impact/review.yaml"]
        )
        self.assertEqual("pass", result["overall_status"])


if __name__ == "__main__":
    unittest.main()
