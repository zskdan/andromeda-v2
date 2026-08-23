#!/usr/bin/env python3
"""Generate the Andromeda OpenRocket v0.2 three-section model."""

from __future__ import annotations

import hashlib
import json
import platform
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "andromeda-v0.1" / "rocket.ork"
OUTPUT = HERE / "rocket.ork"
PACKAGE = HERE.parent / "Andromeda-v0.2.ork"
REPORT = HERE / "evidence" / "model-build-report.json"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(parent, path):
    element = parent.find(path)
    if element is None:
        raise ValueError(f"Missing expected OpenRocket element: {path}")
    return element


def set_text(parent, path, value):
    require(parent, path).text = str(value)


def build():
    tree = ET.parse(SOURCE)
    root = tree.getroot()
    rocket = require(root, "rocket")
    set_text(rocket, "name", "Andromeda v0.2 - three-section Pro54-5G")
    set_text(
        rocket,
        "comment",
        "Preliminary three-section model synchronized with mechanical packaging v0.2. "
        "Section 1 is the 550 mm nose/recovery ogive; section 2 is 1000 mm of "
        "avionics, batteries, and a 200 mm fiberglass RF bay; section 3 is the "
        "600 mm motor/fin assembly. The external mold line, stage mass/CG override, "
        "motor, fins, rail-button stations, and recovery deployment inputs are "
        "unchanged from v0.1. Main and drogue cylindrical packing inside the ogive "
        "is not mechanically verified.",
    )

    stage_components = require(rocket, "subcomponents/stage/subcomponents")
    components = list(stage_components)
    if len(components) != 5 or [item.tag for item in components] != [
        "nosecone",
        "bodytube",
        "bodytube",
        "bodytube",
        "bodytube",
    ]:
        raise ValueError("Unexpected OpenRocket v0.1 stage component layout")
    nose, former_recovery, former_avionics, former_power, propulsion = components

    recovery_subcomponents = require(former_recovery, "subcomponents")
    parachutes = recovery_subcomponents.findall("parachute")
    rail_button = require(recovery_subcomponents, "railbutton")
    if len(parachutes) != 2:
        raise ValueError("Expected main and drogue parachutes in v0.1 recovery body")

    nose_subcomponents = ET.SubElement(nose, "subcomponents")
    for parachute in parachutes:
        recovery_subcomponents.remove(parachute)
        name = require(parachute, "name").text or ""
        if name.startswith("Main parachute"):
            set_text(parachute, "name", "Main parachute 1.55 m - ogive packing conflict open")
            set_text(parachute, "axialoffset", "0.37")
            set_text(parachute, "position", "0.37")
        else:
            set_text(parachute, "name", "Drogue parachute 1.40 m - ogive allocation TBD")
            set_text(parachute, "axialoffset", "0.21")
            set_text(parachute, "position", "0.21")
        nose_subcomponents.append(parachute)

    recovery_subcomponents.remove(rail_button)
    set_text(former_recovery, "name", "SECTION 2A - avionics and batteries - 800 mm")
    set_text(former_recovery, "length", "0.80")
    former_recovery.remove(recovery_subcomponents)
    avionics_subcomponents = ET.SubElement(former_recovery, "subcomponents")
    set_text(rail_button, "name", "Upper rail button - avionics hardpoint")
    avionics_subcomponents.append(rail_button)

    set_text(former_avionics, "name", "SECTION 2B - fiberglass RF antenna bay - 200 mm")
    set_text(former_avionics, "length", "0.20")
    material = require(former_avionics, "material")
    material.set("density", "1850.0")
    material.set("group", "Composites")
    material.text = "Fiberglass"

    stage_components.remove(former_power)
    set_text(propulsion, "name", "SECTION 3 - motor and fins - 600 mm")

    for simulation in root.findall(".//simulation"):
        simulation.set("status", "notsimulated")
        name = require(simulation, "name")
        if "v0.2" not in (name.text or ""):
            name.text = f"{name.text} - v0.2 model update pending rerun"
        for result in list(simulation.findall("flightdata")):
            simulation.remove(result)

    ET.indent(tree, space="  ")
    tree.write(OUTPUT, encoding="utf-8", xml_declaration=True)

    payload = OUTPUT.read_bytes()
    entry = zipfile.ZipInfo("rocket.ork", date_time=(2026, 8, 23, 0, 0, 0))
    entry.compress_type = zipfile.ZIP_DEFLATED
    entry.external_attr = 0o100644 << 16
    with zipfile.ZipFile(PACKAGE, "w") as archive:
        archive.writestr(entry, payload)

    generated_root = ET.parse(OUTPUT).getroot()
    generated_components = generated_root.findall(
        "rocket/subcomponents/stage/subcomponents/*"
    )
    component_summary = [
        {
            "type": item.tag,
            "name": item.findtext("name"),
            "length_m": float(item.findtext("length")),
        }
        for item in generated_components
    ]
    parachute_summary = [
        {
            "name": item.findtext("name"),
            "position_m": float(item.findtext("position")),
            "packed_length_m": float(item.findtext("packedlength")),
            "packed_radius_m": float(item.findtext("packedradius")),
        }
        for item in generated_root.findall(".//nosecone/subcomponents/parachute")
    ]
    with zipfile.ZipFile(PACKAGE) as archive:
        package_valid = archive.namelist() == ["rocket.ork"] and archive.read(
            "rocket.ork"
        ) == payload
    report = {
        "schema_version": 1,
        "tool": {
            "id": "andromeda-openrocket-v0.2-model-builder",
            "version": "1.0.0",
            "python": platform.python_version(),
        },
        "input": {
            "path": SOURCE.relative_to(HERE.parents[2]).as_posix(),
            "sha256": sha256(SOURCE),
        },
        "outputs": {
            "xml": {
                "path": OUTPUT.relative_to(HERE.parents[2]).as_posix(),
                "sha256": sha256(OUTPUT),
                "bytes": OUTPUT.stat().st_size,
            },
            "package": {
                "path": PACKAGE.relative_to(HERE.parents[2]).as_posix(),
                "sha256": sha256(PACKAGE),
                "bytes": PACKAGE.stat().st_size,
            },
        },
        "components": component_summary,
        "nose_parachutes": parachute_summary,
        "simulation_statuses": [
            item.get("status") for item in generated_root.findall(".//simulation")
        ],
        "package_payload_matches_xml": package_valid,
        "overall_status": "pass"
        if package_valid
        and len(component_summary) == 4
        and len(parachute_summary) == 2
        and all(item.get("status") == "notsimulated" for item in generated_root.findall(".//simulation"))
        else "fail",
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build()
