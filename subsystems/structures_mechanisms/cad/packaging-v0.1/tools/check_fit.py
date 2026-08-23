#!/usr/bin/env python3
"""Deterministic envelope checks for Andromeda packaging model v0.1."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any


TOOL_ID = "andromeda-packaging-fit-check"
TOOL_VERSION = "1.0.0"


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


def check_fit(parameters_path: Path) -> dict[str, Any]:
    p, records = load_parameters(parameters_path)

    od = require_number(p, "airframe_outer_diameter_mm")
    wall = require_number(p, "airframe_wall_thickness_mm")
    nominal_id = require_number(p, "airframe_nominal_inner_diameter_mm")
    calculated_id = od - 2.0 * wall

    recovery_length = require_number(p, "recovery_module_length_mm")
    avionics_length = require_number(p, "avionics_module_length_mm")
    power_length = require_number(p, "power_module_length_mm")
    avionics_start = recovery_length
    avionics_end = avionics_start + avionics_length
    power_start = avionics_end
    model_end = power_start + power_length

    disk_od = require_number(p, "flight_disk_outer_diameter_mm")
    k26_diagonal = math.hypot(
        require_number(p, "k26_length_mm"),
        require_number(p, "k26_width_mm"),
    )
    pluto_cross_section_diagonal = math.hypot(
        require_number(p, "pluto_enclosure_width_mm"),
        require_number(p, "pluto_enclosure_height_mm"),
    )
    pluto_start = require_number(p, "pluto_axial_start_mm")
    pluto_end = pluto_start + require_number(p, "pluto_enclosure_length_mm")

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
                "requirement": "SYS-STRUCT-001",
                "status": status,
                "calculation": calculation,
                "margin_mm": None if margin_mm is None else round(margin_mm, 3),
                "notes": notes,
            }
        )

    geometry_error = abs(calculated_id - nominal_id)
    add_check(
        "PKG-GEOM-001",
        "pass" if geometry_error < 1e-9 else "fail",
        f"{od:.3f} - 2*{wall:.3f} = {calculated_id:.3f} mm",
        0.0 if geometry_error < 1e-9 else -geometry_error,
        "Checks the nominal airframe ID derivation; it does not verify manufactured clear bore.",
    )
    add_check(
        "PKG-RADIAL-001",
        "provisional_pass" if disk_od < nominal_id else "fail",
        f"nominal ID {nominal_id:.3f} - disk OD {disk_od:.3f}",
        nominal_id - disk_od,
        "Diametral margin only; couplers, ovality, LEDs, connectors and insertion clearance remain unresolved.",
    )
    add_check(
        "PKG-RADIAL-002",
        "provisional_pass" if k26_diagonal < nominal_id else "fail",
        f"K26 rectangular-envelope diagonal = {k26_diagonal:.3f} mm",
        nominal_id - k26_diagonal,
        "Conservative planar bounding-box check for the SOM, excluding carrier components.",
    )
    add_check(
        "PKG-RADIAL-003",
        "provisional_pass" if pluto_cross_section_diagonal < nominal_id else "fail",
        f"longitudinal Pluto cross-section diagonal = {pluto_cross_section_diagonal:.3f} mm",
        nominal_id - pluto_cross_section_diagonal,
        "Uses the complete published enclosure envelope with its 117 mm dimension parallel to the vehicle axis.",
    )
    pluto_axial_margin = min(pluto_start - avionics_start, avionics_end - pluto_end)
    add_check(
        "PKG-AXIAL-001",
        "provisional_pass" if pluto_axial_margin >= 0 else "fail",
        f"Pluto interval [{pluto_start:.3f}, {pluto_end:.3f}] within avionics [{avionics_start:.3f}, {avionics_end:.3f}] mm",
        pluto_axial_margin,
        "Body envelope only; service length for cables, mounts and removal is still TBD.",
    )

    station_checks = (
        ("recovery", "recovery_disk_station_mm", 0.0, recovery_length),
        ("camera", "camera_disk_station_mm", avionics_start, avionics_end),
        ("compute", "compute_disk_station_mm", avionics_start, avionics_end),
        ("sensor", "sensor_disk_station_mm", avionics_start, avionics_end),
        ("power", "power_disk_station_mm", power_start, model_end),
    )
    for name, key, start, end in station_checks:
        station = require_number(p, key)
        margin = min(station - start, end - station)
        add_check(
            f"PKG-STATION-{name.upper()}",
            "provisional_pass" if margin >= 0 else "fail",
            f"{name} disk station {station:.3f} within [{start:.3f}, {end:.3f}] mm",
            margin,
            "Conceptual station; no component or connector envelope has been allocated yet.",
        )

    open_parameters = [
        {
            "key": record["key"],
            "source": record["source"],
            "notes": record["notes"],
        }
        for record in records
        if record["value"].strip() == "TBD"
    ]
    any_failure = any(check["status"] == "fail" for check in checks)
    overall = "fail" if any_failure else "provisional_pass_with_open_issues"

    return {
        "schema_version": 1,
        "tool": {"id": TOOL_ID, "version": TOOL_VERSION},
        "input": {
            "path": parameters_path.as_posix(),
            "sha256": sha256(parameters_path),
        },
        "requirement_ids": ["SYS-STRUCT-001"],
        "configuration": {
            "axis_convention": "+X from recovery-module forward face toward power module",
            "module_boundaries_mm": {
                "recovery": [0.0, recovery_length],
                "avionics": [avionics_start, avionics_end],
                "power": [power_start, model_end],
            },
            "pluto_orientation": "117 mm enclosure dimension parallel to +X",
        },
        "derived_values": {
            "nominal_inner_diameter_mm": round(calculated_id, 3),
            "disk_diametral_margin_mm": round(nominal_id - disk_od, 3),
            "k26_planar_bounding_diagonal_mm": round(k26_diagonal, 3),
            "pluto_longitudinal_cross_section_diagonal_mm": round(
                pluto_cross_section_diagonal, 3
            ),
            "pluto_body_axial_end_mm": round(pluto_end, 3),
        },
        "overall_status": overall,
        "checks": checks,
        "open_parameters": open_parameters,
        "limitations": [
            "No manufactured-airframe measurement is available.",
            "No cable-bend, mounting-rail, coupler, fastener or connector keep-out is included.",
            "No camera, sensor, recovery-actuator or power-component envelope is included.",
            "No vibration, thermal, structural-load or assembly-sequence verification is performed.",
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
