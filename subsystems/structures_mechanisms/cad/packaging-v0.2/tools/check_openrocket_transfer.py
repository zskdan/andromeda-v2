#!/usr/bin/env python3
"""Compare packaging-v0.2 external geometry with the committed OpenRocket model."""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from check_fit import load_parameters, require_number, sha256


TOOL_ID = "andromeda-openrocket-geometry-transfer-check"
TOOL_VERSION = "2.0.0"


def millimeters(element, tag):
    return float(element.findtext(tag)) * 1000.0


def compare(parameters_path: Path, openrocket_path: Path):
    values, _records = load_parameters(parameters_path)
    n = lambda key: require_number(values, key)
    root = ET.parse(openrocket_path).getroot()
    nose = root.find(".//nosecone")
    bodies = root.findall(".//stage/subcomponents/bodytube")
    fins = root.find(".//trapezoidfinset")
    motor = root.find(".//motormount/motor")
    mount = root.find(".//innertube")
    motormount = root.find(".//motormount")
    main_parachute = next(
        (
            item
            for item in root.findall(".//nosecone/subcomponents/parachute")
            if "main" in item.findtext("name", "").lower()
        ),
        None,
    )
    if None in (nose, fins, motor, mount, motormount, main_parachute) or len(bodies) != 3:
        raise ValueError("Unexpected OpenRocket v0.2 component structure")

    body_by_name = {body.findtext("name"): body for body in bodies}
    avionics = body_by_name["SECTION 2A - avionics and batteries - 800 mm"]
    antenna_bay = body_by_name["SECTION 2B - fiberglass RF antenna bay - 200 mm"]
    propulsion = body_by_name["SECTION 3 - motor and fins - 600 mm"]

    source_values = {
        "airframe_outer_diameter_mm": millimeters(avionics, "radius") * 2.0,
        "nose_ogive_length_mm": millimeters(nose, "length"),
        "nose_wall_thickness_mm": millimeters(nose, "thickness"),
        "nose_shoulder_radius_mm": millimeters(nose, "aftshoulderradius"),
        "nose_shoulder_length_mm": millimeters(nose, "aftshoulderlength"),
        "avionics_section_length_mm": millimeters(avionics, "length")
        + millimeters(antenna_bay, "length"),
        "antenna_bay_start_mm": millimeters(nose, "length")
        + millimeters(avionics, "length"),
        "antenna_bay_total_length_mm": millimeters(antenna_bay, "length"),
        "motor_section_length_mm": millimeters(propulsion, "length"),
        "main_parachute_axial_start_mm": millimeters(main_parachute, "position"),
        "main_parachute_packed_length_mm": millimeters(main_parachute, "packedlength"),
        "main_parachute_packed_diameter_mm": millimeters(main_parachute, "packedradius") * 2.0,
        "motor_mount_outer_diameter_mm": millimeters(mount, "outerradius") * 2.0,
        "motor_mount_wall_thickness_mm": millimeters(mount, "thickness"),
        "motor_mount_length_mm": millimeters(mount, "length"),
        "pro54_motor_diameter_mm": millimeters(motor, "diameter"),
        "pro54_motor_length_mm": millimeters(motor, "length"),
        "pro54_motor_aft_overhang_mm": millimeters(motormount, "overhang"),
        "fin_count": float(fins.findtext("fincount")),
        "fin_root_chord_mm": millimeters(fins, "rootchord"),
        "fin_tip_chord_mm": millimeters(fins, "tipchord"),
        "fin_sweep_length_mm": millimeters(fins, "sweeplength"),
        "fin_span_mm": millimeters(fins, "height"),
        "fin_thickness_mm": millimeters(fins, "thickness"),
        "fin_aft_clearance_mm": -millimeters(fins, "axialoffset"),
    }
    source_values["overall_vehicle_length_mm"] = (
        source_values["nose_ogive_length_mm"]
        + source_values["avionics_section_length_mm"]
        + source_values["motor_section_length_mm"]
    )

    checks = []
    for key, source_value in source_values.items():
        parameter_value = n(key)
        error = parameter_value - source_value
        checks.append(
            {
                "key": key,
                "status": "pass" if abs(error) < 1.0e-9 else "fail",
                "openrocket_value": round(source_value, 6),
                "parameter_value": round(parameter_value, 6),
                "error": round(error, 9),
            }
        )

    overall = "pass" if all(item["status"] == "pass" for item in checks) else "fail"
    return {
        "schema_version": 1,
        "tool": {"id": TOOL_ID, "version": TOOL_VERSION},
        "inputs": {
            "parameters": {"path": parameters_path.as_posix(), "sha256": sha256(parameters_path)},
            "openrocket": {"path": openrocket_path.as_posix(), "sha256": sha256(openrocket_path)},
        },
        "overall_status": overall,
        "checks": checks,
        "notes": [
            "The 1000 mm mechanical avionics section is represented by an 800 mm avionics tube and a 200 mm fiberglass RF bay.",
            "The OpenRocket parachute hierarchy matches the nose/recovery section, but the mechanical packing conflict remains open.",
            "This check transfers geometry only; it does not establish structural adequacy or flight stability.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parameters", required=True, type=Path)
    parser.add_argument("--openrocket", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = compare(args.parameters, args.openrocket)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if result["overall_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
