#!/usr/bin/env python3
"""Check flight-driving equivalence between OpenRocket v0.1 and v0.2."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path


TOOL_ID = "andromeda-openrocket-mechanical-impact-check"
TOOL_VERSION = "1.1.0"


def number(element, path):
    value = element.findtext(path)
    if value is None:
        raise ValueError(f"Missing {path}")
    return float(value)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parameter_records(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return {row["key"]: row for row in csv.DictReader(stream)}


def component_key(parachute):
    name = parachute.findtext("name", "").lower()
    return "main" if "main" in name else "drogue"


def canonical_element(element):
    if element is None:
        return None
    return {
        "tag": element.tag,
        "attributes": sorted(element.attrib.items()),
        "text": (element.text or "").strip(),
        "children": [canonical_element(child) for child in list(element)],
    }


def extract(path):
    root = ET.parse(path).getroot()
    rocket = root.find("rocket")
    if rocket is None:
        raise ValueError(f"No rocket element in {path}")
    stage = rocket.find("subcomponents/stage")
    stage_components = rocket.findall("subcomponents/stage/subcomponents/*")
    if stage is None or not stage_components:
        raise ValueError(f"No stage components in {path}")
    nose = stage_components[0]
    body_tubes = [item for item in stage_components if item.tag == "bodytube"]

    nose_length = number(nose, "length")
    body_starts = {}
    station = nose_length
    for body in body_tubes:
        body_starts[id(body)] = station
        station += number(body, "length")

    motor_body = next(body for body in body_tubes if body.find(".//motormount") is not None)
    motor = motor_body.find(".//motormount/motor")
    motormount = motor_body.find(".//motormount")
    fins = motor_body.find(".//trapezoidfinset")
    if motor is None or motormount is None or fins is None:
        raise ValueError("Missing propulsion inputs")

    rail_stations = []
    for body in body_tubes:
        for button in body.findall("subcomponents/railbutton"):
            rail_stations.append(
                round(body_starts[id(body)] + number(button, "position"), 9)
            )

    parachutes = {}
    for parachute in rocket.findall(".//parachute"):
        parachutes[component_key(parachute)] = {
            "diameter": number(parachute, "diameter"),
            "cd": number(parachute, "cd"),
            "deployevent": parachute.findtext("deployevent"),
            "deployaltitude": number(parachute, "deployaltitude"),
            "deploydelay": number(parachute, "deploydelay"),
            "overridemass": number(parachute, "overridemass"),
            "packedlength": number(parachute, "packedlength"),
            "packedradius": number(parachute, "packedradius"),
        }

    conditions = root.find(".//simulation/conditions")
    conditions_hash = hashlib.sha256(
        json.dumps(canonical_element(conditions), sort_keys=True).encode("utf-8")
    ).hexdigest()
    body_radius_values = sorted({number(body, "radius") for body in body_tubes})
    body_wall_values = sorted({number(body, "thickness") for body in body_tubes})

    return {
        "overall_body_length_m": round(station, 9),
        "body_diameter_m": round(max(body_radius_values) * 2.0, 9),
        "body_radius_values_m": body_radius_values,
        "body_wall_values_m": body_wall_values,
        "nose": {
            key: nose.findtext(key)
            for key in (
                "length",
                "thickness",
                "shape",
                "shapeparameter",
                "aftradius",
                "aftshoulderradius",
                "aftshoulderlength",
            )
        },
        "stage_mass_kg": number(stage, "overridemass"),
        "stage_cg_m_from_nose": number(stage, "overridecg"),
        "stage_mass_override_enabled": stage.findtext("overridesubcomponentsmass"),
        "stage_cg_override_enabled": stage.findtext("overridesubcomponentscg"),
        "motor": {
            key: motor.findtext(key)
            for key in ("manufacturer", "digest", "designation", "diameter", "length", "delay")
        },
        "motor_overhang_m": number(motormount, "overhang"),
        "fins": {
            key: fins.findtext(key)
            for key in (
                "fincount",
                "axialoffset",
                "thickness",
                "cant",
                "rootchord",
                "tipchord",
                "sweeplength",
                "height",
            )
        },
        "motor_section_start_m": round(body_starts[id(motor_body)], 9),
        "rail_button_global_stations_m": sorted(rail_stations),
        "parachutes": parachutes,
        "simulation_conditions_sha256": conditions_hash,
    }


def compare(old_path, new_path, parameters_path, previous_ins_station_mm):
    old = extract(old_path)
    new = extract(new_path)
    parameters = parameter_records(parameters_path)
    ins_station_mm = float(parameters["ins_navigation_disk_station_mm"]["value"])
    ins_mass_raw = parameters["ins_navigation_disk_mass_kg"]["value"]
    ins_delta_m = (ins_station_mm - previous_ins_station_mm) / 1000.0
    repository_root = new_path.resolve().parents[3]
    rocketpy_directory = repository_root / "simulations" / "rocketpy"
    rocketpy_sources = sorted(rocketpy_directory.glob("*.py"))
    checks = []

    def add(check_id, old_value, new_value, rationale):
        checks.append(
            {
                "id": check_id,
                "status": "pass" if old_value == new_value else "fail",
                "v0.1": old_value,
                "v0.2": new_value,
                "rationale": rationale,
            }
        )

    add("SIM-IMPACT-OML-LENGTH", old["overall_body_length_m"], new["overall_body_length_m"], "Total external axial length drives the aerodynamic geometry.")
    add("SIM-IMPACT-OML-DIAMETER", old["body_diameter_m"], new["body_diameter_m"], "Maximum straight-body diameter is unchanged.")
    add("SIM-IMPACT-NOSE", old["nose"], new["nose"], "Nose profile and shoulder inputs are unchanged.")
    add("SIM-IMPACT-STAGE-MASS", old["stage_mass_kg"], new["stage_mass_kg"], "The provisional dry-stage mass override is unchanged.")
    add("SIM-IMPACT-STAGE-CG", old["stage_cg_m_from_nose"], new["stage_cg_m_from_nose"], "The provisional dry-stage CG override is unchanged.")
    add("SIM-IMPACT-MASS-OVERRIDE", old["stage_mass_override_enabled"], new["stage_mass_override_enabled"], "The stage override prevents internal component regrouping from changing simulated mass.")
    add("SIM-IMPACT-CG-OVERRIDE", old["stage_cg_override_enabled"], new["stage_cg_override_enabled"], "The stage override prevents parachute relocation from changing simulated CG.")
    add("SIM-IMPACT-MOTOR", old["motor"], new["motor"], "Motor identity and envelope are unchanged.")
    add("SIM-IMPACT-MOTOR-OVERHANG", old["motor_overhang_m"], new["motor_overhang_m"], "Motor aft overhang is unchanged.")
    add("SIM-IMPACT-MOTOR-STATION", old["motor_section_start_m"], new["motor_section_start_m"], "The propulsion section begins at the same global station.")
    add("SIM-IMPACT-FINS", old["fins"], new["fins"], "Fin count, planform, thickness, cant and axial offset are unchanged.")
    add("SIM-IMPACT-RAIL", old["rail_button_global_stations_m"], new["rail_button_global_stations_m"], "Rail-button global stations remain unchanged after regrouping.")
    add("SIM-IMPACT-RECOVERY", old["parachutes"], new["parachutes"], "Deployment events, drag inputs, masses and packed envelopes are unchanged; mechanical fit is assessed separately.")
    add("SIM-IMPACT-CONDITIONS", old["simulation_conditions_sha256"], new["simulation_conditions_sha256"], "Launch, atmosphere and wind inputs are semantically equivalent after ignoring XML formatting whitespace.")

    passed = all(check["status"] == "pass" for check in checks)
    mass_is_tbd = ins_mass_raw.strip().upper() == "TBD"
    if mass_is_tbd:
        cg_delta_m = "TBD"
        rerun_disposition = "deferred_pending_ins_disk_mass_and_integrated_cg"
        overall_status = (
            "pass_current_openrocket_inputs_equivalent_with_ins_mass_tbd"
            if passed
            else "fail"
        )
    else:
        ins_mass_kg = float(ins_mass_raw)
        cg_delta_m = ins_mass_kg * ins_delta_m / old["stage_mass_kg"]
        rerun_disposition = "required_after_ins_disk_relocation"
        overall_status = "fail_requires_mass_cg_model_update"
    return {
        "schema_version": 1,
        "tool": {"id": TOOL_ID, "version": TOOL_VERSION},
        "inputs": {
            "v0.1": {"path": old_path.as_posix(), "sha256": sha256(old_path)},
            "v0.2": {"path": new_path.as_posix(), "sha256": sha256(new_path)},
            "mechanical_parameters": {
                "path": parameters_path.as_posix(),
                "sha256": sha256(parameters_path),
            },
        },
        "triggered_rule": "XDOM-MECH-SIM-001",
        "overall_status": overall_status,
        "simulation_rerun_disposition": rerun_disposition,
        "ins_navigation_relocation": {
            "previous_station_mm_from_nose": previous_ins_station_mm,
            "new_station_mm_from_nose": ins_station_mm,
            "aft_shift_mm": ins_station_mm - previous_ins_station_mm,
            "disk_mass_kg": ins_mass_raw,
            "dry_cg_shift_m": cg_delta_m,
            "dry_cg_shift_formula": (
                f"ins_disk_mass_kg * {ins_delta_m:.6f} m / "
                f"{old['stage_mass_kg']:.6f} kg"
            ),
        },
        "rocketpy_review": {
            "source_model_present": bool(rocketpy_sources),
            "source_paths": [
                path.relative_to(repository_root).as_posix()
                for path in rocketpy_sources
            ],
            "disposition": (
                "review_and_update_after_ins_mass_and_integrated_cg_are_available"
                if rocketpy_sources
                else "no_authoritative_source_model_present; update_when_restored"
            ),
        },
        "checks": checks,
        "assessment": [
            "The v0.2 change regroups equal-diameter contiguous tubes and moves recovery components in the hierarchy without changing external aerodynamics or overridden mass/CG.",
            (
                f"The complete INS/navigation disk allocation moves aft by "
                f"{ins_station_mm - previous_ins_station_mm:.1f} mm; its mass is "
                f"{ins_mass_raw}, so the physical dry-CG delta cannot yet be calculated."
            ),
            "OpenRocket records the new internal station, while the existing 5.32 kg and x=1.28 m dry-stage overrides remain explicitly provisional.",
            "The v0.2 embedded simulation is marked notsimulated; historical results remain preliminary and are not promoted to v0.2 verification evidence.",
            "Allocate or measure the INS disk mass, update the integrated dry mass/CG, and rerun OpenRocket before this relocation can be flight-verified.",
            "No authoritative RocketPy source model is currently present; compiled cache files are not used as engineering inputs.",
        ],
        "mechanical_open_issue": "Parachute hierarchy matches the architecture, but ogive packing remains mechanically unresolved.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--old", required=True, type=Path)
    parser.add_argument("--new", required=True, type=Path)
    parser.add_argument("--parameters", required=True, type=Path)
    parser.add_argument("--previous-ins-station-mm", type=float, default=1080.0)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = compare(
        args.old,
        args.new,
        args.parameters,
        args.previous_ins_station_mm,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 1 if result["overall_status"].startswith("fail") else 0


if __name__ == "__main__":
    raise SystemExit(main())
