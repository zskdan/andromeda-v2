import csv
import json
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGING = (
    ROOT
    / "subsystems"
    / "structures_mechanisms"
    / "cad"
    / "packaging-v0.2"
)
OPENROCKET = ROOT / "simulations" / "openrocket" / "andromeda-v0.2"


class InsNavigationAllocationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with (PACKAGING / "parameters.csv").open(newline="", encoding="utf-8") as stream:
            cls.parameters = {row["key"]: row["value"] for row in csv.DictReader(stream)}
        cls.fit = json.loads(
            (PACKAGING / "evidence" / "fit-report.json").read_text(encoding="utf-8")
        )
        cls.freecad = json.loads(
            (PACKAGING / "evidence" / "freecad-build-report.json").read_text(
                encoding="utf-8"
            )
        )
        cls.openrocket_root = ET.parse(OPENROCKET / "rocket.ork").getroot()
        cls.impact = json.loads(
            (OPENROCKET / "evidence" / "mechanical-simulation-impact-report.json").read_text(
                encoding="utf-8"
            )
        )

    def test_ins_station_and_feed_allocations(self):
        self.assertEqual("1320.0", self.parameters["ins_navigation_disk_station_mm"])
        self.assertEqual("1395.0", self.parameters["gnss_upper_ring_feed_station_mm"])
        self.assertEqual("1505.0", self.parameters["gnss_lower_ring_feed_station_mm"])

    def test_bare_disk_clearances_are_traceable(self):
        derived = self.fit["derived_values"]
        self.assertEqual(22.2, derived["ins_disk_forward_clearance_to_pluto_body_mm"])
        self.assertEqual(29.2, derived["ins_disk_aft_clearance_to_antenna_bay_mm"])
        self.assertEqual(75.0, derived["gnss_upper_feed_minimum_axial_coax_span_mm"])
        self.assertEqual(185.0, derived["gnss_lower_feed_minimum_axial_coax_span_mm"])

    def test_openrocket_records_the_same_internal_station(self):
        comment = self.openrocket_root.findtext("rocket/comment", "")
        self.assertIn("INS_NAVIGATION_DISK_STATION_M=1.320000", comment)
        self.assertIn("INS_NAVIGATION_DISK_MASS_KG=TBD", comment)

    def test_freecad_contains_relocated_ins_disk(self):
        self.assertEqual("pass", self.freecad["overall_status"])
        self.assertNotIn("Sensor_Disk", self.freecad["objects"])
        bounds = self.freecad["objects"]["INS_Navigation_Disk"]["bounding_box_mm"]
        self.assertEqual(1319.2, bounds["x_min"])
        self.assertEqual(1320.8, bounds["x_max"])
        self.assertTrue(self.freecad["step_round_trip"]["all_shapes_valid"])
        self.assertTrue(self.freecad["step_round_trip"]["all_bounds_finite"])

    def test_flight_rerun_is_deferred_only_for_TBD_mass(self):
        relocation = self.impact["ins_navigation_relocation"]
        self.assertEqual("TBD", relocation["disk_mass_kg"])
        self.assertEqual(240.0, relocation["aft_shift_mm"])
        self.assertEqual(
            "deferred_pending_ins_disk_mass_and_integrated_cg",
            self.impact["simulation_rerun_disposition"],
        )


if __name__ == "__main__":
    unittest.main()
