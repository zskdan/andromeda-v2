#!/usr/bin/env python3
"""Deterministic geometry checks for Andromeda packaging model v0.2."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any


TOOL_ID = "andromeda-packaging-fit-check"
TOOL_VERSION = "2.1.0"
REQUIREMENT_ID = "SYS-STRUCT-001"
REQUIREMENT_IDS = [
    REQUIREMENT_ID,
    "SYS-MASS-001",
    "TDO-NAV-001",
    "TDO-TIME-001",
    "TDO-RF-001",
]


def load_parameters(path: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    records: list[dict[str, str]] = []
    values: dict[str, Any] = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for record in csv.DictReader(stream):
            records.append(record)
            raw = record["value"].strip()
            if raw == "TBD":
                value: Any = raw
            else:
                try:
                    value = float(raw)
                except ValueError:
                    value = raw
            values[record["key"]] = value
    return values, records


def require_number(values: dict[str, Any], key: str) -> float:
    value = values[key]
    if not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be numeric, got {value!r}")
    return float(value)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def von_karman_radius(x: float, length: float, base_radius: float) -> float:
    """Return the C=0 Haack-series radius at axial station x."""
    clamped = min(max(x, 0.0), length)
    theta = math.acos(1.0 - 2.0 * clamped / length)
    return base_radius / math.sqrt(math.pi) * math.sqrt(
        theta - 0.5 * math.sin(2.0 * theta)
    )


def check_fit(parameters_path: Path) -> dict[str, Any]:
    p, records = load_parameters(parameters_path)
    n = lambda key: require_number(p, key)

    od = n("airframe_outer_diameter_mm")
    wall = n("airframe_wall_thickness_mm")
    nominal_id = n("airframe_nominal_inner_diameter_mm")
    calculated_id = od - 2.0 * wall
    nose_length = n("nose_ogive_length_mm")
    avionics_length = n("avionics_section_length_mm")
    motor_length = n("motor_section_length_mm")
    overall_length = n("overall_vehicle_length_mm")
    separation_station = n("separation_interface_station_mm")
    motor_interface = n("motor_interface_station_mm")
    avionics_end = separation_station + avionics_length
    body_end = avionics_end + motor_length
    separation_end = separation_station + n("nose_shoulder_length_mm")
    antenna_start = n("antenna_bay_start_mm")
    antenna_end = antenna_start + n("antenna_bay_total_length_mm")

    checks: list[dict[str, Any]] = []

    def add_check(
        check_id: str,
        status: str,
        calculation: str,
        margin_mm: float | None,
        notes: str,
    ) -> None:
        checks.append(
            {
                "id": check_id,
                "requirement": REQUIREMENT_ID,
                "status": status,
                "calculation": calculation,
                "margin_mm": None if margin_mm is None else round(margin_mm, 3),
                "notes": notes,
            }
        )

    id_error = abs(calculated_id - nominal_id)
    add_check(
        "PKG-GEOM-001",
        "pass" if id_error < 1e-9 else "fail",
        f"{od:.3f} - 2*{wall:.3f} = {calculated_id:.3f} mm",
        0.0 if id_error < 1e-9 else -id_error,
        "Nominal derivation only; manufactured clear bore is still unverified.",
    )

    length_error = max(
        abs(nose_length - separation_station),
        abs(avionics_end - motor_interface),
        abs(body_end - overall_length),
    )
    add_check(
        "PKG-GEOM-002",
        "pass" if length_error < 1e-9 else "fail",
        f"{nose_length:.1f} + {avionics_length:.1f} + {motor_length:.1f} = {body_end:.1f} mm",
        0.0 if length_error < 1e-9 else -length_error,
        "Checks the three-section grouping against the 2.15 m OpenRocket outer mold line.",
    )

    disk_od = n("flight_disk_outer_diameter_mm")
    disk_thickness = n("flight_disk_thickness_mm")
    add_check(
        "PKG-RADIAL-001",
        "provisional_pass" if disk_od < nominal_id else "fail",
        f"nominal ID {nominal_id:.3f} - disk OD {disk_od:.3f}",
        nominal_id - disk_od,
        "Diametral margin excludes couplers, LEDs, connectors, rails, fasteners and insertion clearance.",
    )

    k26_diagonal = math.hypot(n("k26_length_mm"), n("k26_width_mm"))
    add_check(
        "PKG-RADIAL-002",
        "provisional_pass" if k26_diagonal < nominal_id else "fail",
        f"K26 rectangular-envelope diagonal = {k26_diagonal:.3f} mm",
        nominal_id - k26_diagonal,
        "Published SOM envelope only; carrier and connectors are not modeled.",
    )

    pluto_diagonal = math.hypot(
        n("pluto_enclosure_width_mm"), n("pluto_enclosure_height_mm")
    )
    add_check(
        "PKG-RADIAL-003",
        "provisional_pass" if pluto_diagonal < nominal_id else "fail",
        f"longitudinal Pluto cross-section diagonal = {pluto_diagonal:.3f} mm",
        nominal_id - pluto_diagonal,
        "Complete enclosure envelope; USB and coax service volumes remain TBD.",
    )

    equipment_start = separation_end
    equipment_end = antenna_start
    disk_specs = (
        ("recovery_control", "recovery_control_disk_station_mm"),
        ("recovery_power", "recovery_power_disk_station_mm"),
        ("avionics_power", "avionics_power_disk_station_mm"),
        ("camera", "camera_disk_station_mm"),
        ("compute", "compute_disk_station_mm"),
        ("rf", "rf_disk_station_mm"),
        ("ins_navigation", "ins_navigation_disk_station_mm"),
    )
    for name, key in disk_specs:
        station = n(key)
        margin = min(station - equipment_start, equipment_end - station)
        add_check(
            f"PKG-STATION-{name.upper()}",
            "provisional_pass" if margin >= 0 else "fail",
            f"{name} disk at {station:.1f} within equipment interval [{equipment_start:.1f}, {equipment_end:.1f}] mm",
            margin,
            "Conceptual station; connector and service envelopes are not yet allocated.",
        )

    battery_start = n("battery_bay_start_mm")
    battery_end = battery_start + n("battery_bay_length_mm")
    battery_radial_margin = nominal_id - n("battery_bay_diameter_mm")
    battery_axial_margin = min(
        battery_start - equipment_start, equipment_end - battery_end
    )
    add_check(
        "PKG-BATTERY-001",
        "provisional_pass" if min(battery_radial_margin, battery_axial_margin) >= 0 else "fail",
        f"battery allocation [{battery_start:.1f}, {battery_end:.1f}] mm, OD {n('battery_bay_diameter_mm'):.1f} mm",
        min(battery_radial_margin, battery_axial_margin),
        "Allocation volume only; cell chemistry, count, restraints, protection and venting are TBD.",
    )

    pluto_start = n("pluto_axial_start_mm")
    pluto_end = pluto_start + n("pluto_enclosure_length_mm")
    pluto_axial_margin = min(pluto_start - equipment_start, equipment_end - pluto_end)
    add_check(
        "PKG-AXIAL-PLUTO",
        "provisional_pass" if pluto_axial_margin >= 0 else "fail",
        f"Pluto interval [{pluto_start:.1f}, {pluto_end:.1f}] within [{equipment_start:.1f}, {equipment_end:.1f}] mm",
        pluto_axial_margin,
        "Body envelope only; service length for cables, thermal path, mounts and removal is TBD.",
    )

    ins_station = n("ins_navigation_disk_station_mm")
    ins_forward_face = ins_station - disk_thickness / 2.0
    ins_aft_face = ins_station + disk_thickness / 2.0
    ins_pluto_body_clearance = ins_forward_face - pluto_end
    ins_antenna_bay_clearance = antenna_start - ins_aft_face
    add_check(
        "PKG-INS-AXIAL-001",
        "provisional_pass"
        if min(ins_pluto_body_clearance, ins_antenna_bay_clearance) >= 0
        else "fail",
        (
            f"INS disk [{ins_forward_face:.1f}, {ins_aft_face:.1f}] mm between "
            f"Pluto body ending {pluto_end:.1f} mm and antenna/rail region starting "
            f"{antenna_start:.1f} mm"
        ),
        min(ins_pluto_body_clearance, ins_antenna_bay_clearance),
        "Bare 1.6 mm disk only; the INS assembly depth and Pluto service envelope remain TBD.",
    )

    antenna_zone_length = (
        n("antenna_bay_total_length_mm") - n("antenna_bay_gap_mm")
    ) / 2.0
    expected_upper_feed = antenna_start + antenna_zone_length / 2.0
    expected_lower_feed = (
        antenna_start
        + antenna_zone_length
        + n("antenna_bay_gap_mm")
        + antenna_zone_length / 2.0
    )
    upper_feed = n("gnss_upper_ring_feed_station_mm")
    lower_feed = n("gnss_lower_ring_feed_station_mm")
    feed_station_error = max(
        abs(upper_feed - expected_upper_feed),
        abs(lower_feed - expected_lower_feed),
    )
    add_check(
        "PKG-GNSS-FEEDS-001",
        "provisional_pass" if feed_station_error < 1.0e-9 else "fail",
        (
            f"GNSS candidate feed stations {upper_feed:.1f} and {lower_feed:.1f} mm "
            f"at the centers of the two 90 mm antenna zones"
        ),
        0.0 if feed_station_error < 1.0e-9 else -feed_station_error,
        "Feed stations are allocation centers, not released antenna phase centers or routed cable lengths.",
    )

    antenna_error = abs(antenna_end - motor_interface)
    add_check(
        "PKG-RF-BAY-001",
        "provisional_pass" if antenna_error < 1e-9 else "fail",
        f"antenna bay [{antenna_start:.1f}, {antenna_end:.1f}] ends at motor interface {motor_interface:.1f} mm",
        0.0 if antenna_error < 1e-9 else -antenna_error,
        "Two generic fiberglass RF zones; antenna elements and RF keep-outs remain TBD.",
    )

    rail_start = n("aluminum_interface_rail_start_mm")
    rail_end = rail_start + n("aluminum_interface_rail_length_mm")
    rail_outer_radius = n("aluminum_interface_rail_center_radius_mm") + 0.5 * n(
        "aluminum_interface_rail_height_mm"
    )
    rail_interface_margin = min(motor_interface - rail_start, rail_end - motor_interface)
    rail_bore_margin = nominal_id / 2.0 - rail_outer_radius
    add_check(
        "PKG-STRUCT-INTERFACE-001",
        "provisional_pass" if min(rail_interface_margin, rail_bore_margin) >= 0 else "fail",
        f"four interrupted rails [{rail_start:.1f}, {rail_end:.1f}] cross x={motor_interface:.1f}; outer radius {rail_outer_radius:.1f} mm",
        min(rail_interface_margin, rail_bore_margin),
        "Rails are a packaging concept, not a sized load path. A continuous aluminum sleeve is intentionally excluded from the RF bay.",
    )

    motor_aft = overall_length + n("pro54_motor_aft_overhang_mm")
    motor_forward = motor_aft - n("pro54_motor_length_mm")
    mount_start = overall_length - n("motor_mount_length_mm")
    motor_mount_margin = min(
        motor_forward - mount_start,
        n("motor_mount_outer_diameter_mm") - n("pro54_motor_diameter_mm"),
    )
    add_check(
        "PKG-MOTOR-001",
        "provisional_pass" if motor_mount_margin >= 0 else "fail",
        f"Pro54 interval [{motor_forward:.1f}, {motor_aft:.1f}] mm in aft-aligned 500 mm mount with 10 mm overhang",
        motor_mount_margin,
        "Envelope is from the configured OpenRocket K570 record; retention and nozzle clearance are TBD.",
    )

    fin_root_start = overall_length - n("fin_aft_clearance_mm") - n("fin_root_chord_mm")
    fin_tip_end = fin_root_start + n("fin_sweep_length_mm") + n("fin_tip_chord_mm")
    fin_axial_margin = overall_length - n("fin_aft_clearance_mm") - fin_tip_end
    add_check(
        "PKG-FIN-001",
        "pass" if int(n("fin_count")) == 4 and fin_axial_margin >= 0 else "fail",
        f"four fins, root [{fin_root_start:.1f}, {overall_length - n('fin_aft_clearance_mm'):.1f}] mm, tip ends {fin_tip_end:.1f} mm",
        fin_axial_margin,
        "Matches the provisional OpenRocket trapezoidal planform and axial interpretation.",
    )

    chute_start = n("main_parachute_axial_start_mm")
    chute_end = chute_start + n("main_parachute_packed_length_mm")
    chute_radius = n("main_parachute_packed_diameter_mm") / 2.0
    nose_inner_radius_at_start = max(
        0.0,
        von_karman_radius(chute_start, nose_length, od / 2.0)
        - n("nose_wall_thickness_mm"),
    )
    chute_radial_margin = nose_inner_radius_at_start - chute_radius
    chute_axial_margin = nose_length - chute_end
    chute_margin = min(chute_radial_margin, chute_axial_margin)
    add_check(
        "PKG-RECOVERY-001",
        "provisional_pass" if chute_margin >= 0 else "open_conflict",
        f"main pack [{chute_start:.1f}, {chute_end:.1f}] mm, radius {chute_radius:.1f} mm; ogive inner radius at forward face {nose_inner_radius_at_start:.3f} mm",
        chute_margin,
        "The existing OpenRocket cylindrical pack does not fit wholly inside the ogive at this trial station. Repacking or an aft cylindrical recovery volume is required.",
    )

    open_parameters = [
        {"key": r["key"], "source": r["source"], "notes": r["notes"]}
        for r in records
        if r["value"].strip() == "TBD"
    ]
    hard_failure = any(item["status"] == "fail" for item in checks)
    open_conflict = any(item["status"] == "open_conflict" for item in checks)
    if hard_failure:
        overall = "fail"
    elif open_conflict:
        overall = "provisional_with_packaging_conflict"
    else:
        overall = "provisional_pass_with_open_issues"

    return {
        "schema_version": 1,
        "tool": {"id": TOOL_ID, "version": TOOL_VERSION},
        "input": {"path": parameters_path.as_posix(), "sha256": sha256(parameters_path)},
        "requirement_ids": REQUIREMENT_IDS,
        "configuration": {
            "axis_convention": "+X from nose tip toward motor nozzle",
            "section_boundaries_mm": {
                "nose_recovery": [0.0, separation_station],
                "avionics_batteries": [separation_station, motor_interface],
                "motor_fins": [motor_interface, overall_length],
            },
            "interfaces_mm": {
                "separation_module": separation_station,
                "fiberglass_rf_and_aluminum_rails": motor_interface,
            },
            "pluto_orientation": "117 mm enclosure dimension parallel to +X",
        },
        "derived_values": {
            "nominal_inner_diameter_mm": round(calculated_id, 3),
            "disk_diametral_margin_mm": round(nominal_id - disk_od, 3),
            "k26_planar_bounding_diagonal_mm": round(k26_diagonal, 3),
            "pluto_longitudinal_cross_section_diagonal_mm": round(pluto_diagonal, 3),
            "ins_disk_forward_clearance_to_pluto_body_mm": round(
                ins_pluto_body_clearance, 3
            ),
            "ins_disk_aft_clearance_to_antenna_bay_mm": round(
                ins_antenna_bay_clearance, 3
            ),
            "gnss_upper_feed_minimum_axial_coax_span_mm": round(
                upper_feed - ins_station, 3
            ),
            "gnss_lower_feed_minimum_axial_coax_span_mm": round(
                lower_feed - ins_station, 3
            ),
            "main_parachute_trial_margin_mm": round(chute_margin, 3),
            "fin_tip_to_body_aft_margin_mm": round(fin_axial_margin, 3),
            "motor_forward_station_mm": round(motor_forward, 3),
        },
        "overall_status": overall,
        "checks": checks,
        "open_parameters": open_parameters,
        "limitations": [
            "The current main-parachute packed cylinder conflicts with the ogive trial placement; the drogue is unallocated.",
            "Antenna elements, patterns, cable keep-outs and RF interaction with the aluminum rails are not modeled.",
            "The relocated INS disk is represented as a bare PCB plane; component, shield, connector, harness and mounting depth remain TBD.",
            "The 22.2 mm Pluto-body clearance does not include its TBD service envelope, so assembly fit is not verified.",
            "INS disk mass is TBD; this fit check does not update or verify vehicle mass, CG or stability.",
            "No manufactured-airframe or coupler measurements are available.",
            "No loads, joint sizing, flutter, vibration, thermal or assembly-sequence verification is performed.",
            "Battery and most electronic component envelopes remain allocations rather than selected hardware.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parameters", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = check_fit(args.parameters)
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 1 if result["overall_status"] == "fail" else 0


if __name__ == "__main__":
    raise SystemExit(main())
