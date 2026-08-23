#!/usr/bin/env python3
"""Build the Andromeda v0.2 three-section packaging model in FreeCAD."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

try:
    import FreeCAD as App
    import Import
    import Part
except ImportError as exc:  # pragma: no cover - FreeCAD runtime only
    raise SystemExit(
        "Run this script with FreeCADCmd/FreeCAD, not the system Python interpreter."
    ) from exc


MODEL_REVISION = "0.2"
HERE = Path(__file__).resolve().parent
PACKAGE_ROOT = HERE.parent
REPO_ROOT = PACKAGE_ROOT.parents[3]
sys.path.insert(0, str(PACKAGE_ROOT / "tools"))

from check_fit import (  # noqa: E402
    check_fit,
    load_parameters,
    require_number,
    sha256,
    von_karman_radius,
)


def set_view(obj, color, transparency=0):
    """Apply GUI properties without making the headless build depend on them."""
    try:
        obj.ViewObject.ShapeColor = color
        obj.ViewObject.LineColor = tuple(max(0.0, c * 0.55) for c in color)
        obj.ViewObject.Transparency = transparency
    except Exception:
        pass


def add_shape(doc, group, name, label, shape, color, transparency=0):
    obj = doc.addObject("Part::Feature", name)
    obj.Label = label
    obj.Shape = shape
    group.addObject(obj)
    set_view(obj, color, transparency)
    return obj


def centered_box(x_start, x_length, y_width, z_height):
    return Part.makeBox(
        x_length,
        y_width,
        z_height,
        App.Vector(x_start, -y_width / 2.0, -z_height / 2.0),
    )


def cylindrical_shell(x_start, length, outer_radius, inner_radius):
    axis = App.Vector(1, 0, 0)
    outer = Part.makeCylinder(outer_radius, length, App.Vector(x_start, 0, 0), axis)
    inner = Part.makeCylinder(inner_radius, length, App.Vector(x_start, 0, 0), axis)
    return outer.cut(inner)


def von_karman_solid(length, base_radius, wall_thickness, samples=96):
    """Create a hollow C=0 Haack-series ogive by revolving sampled profiles."""
    axis = App.Vector(1, 0, 0)

    def revolved_profile(x_start, radius_offset):
        points = [App.Vector(x_start, 0, 0)]
        for index in range(1, samples + 1):
            x = x_start + (length - x_start) * index / samples
            radius = max(0.0, von_karman_radius(x, length, base_radius) - radius_offset)
            points.append(App.Vector(x, radius, 0))
        points.extend((App.Vector(length, 0, 0), App.Vector(x_start, 0, 0)))
        return Part.Face(Part.makePolygon(points)).revolve(
            App.Vector(0, 0, 0), axis, 360.0
        )

    outer = revolved_profile(0.0, 0.0)
    inner = revolved_profile(wall_thickness, wall_thickness)
    return outer.cut(inner)


def trapezoidal_fin_compound(
    root_start,
    body_radius,
    root_chord,
    tip_chord,
    sweep,
    span,
    thickness,
    count,
):
    points = (
        App.Vector(root_start, body_radius, -thickness / 2.0),
        App.Vector(root_start + sweep, body_radius + span, -thickness / 2.0),
        App.Vector(
            root_start + sweep + tip_chord,
            body_radius + span,
            -thickness / 2.0,
        ),
        App.Vector(root_start + root_chord, body_radius, -thickness / 2.0),
        App.Vector(root_start, body_radius, -thickness / 2.0),
    )
    base = Part.Face(Part.makePolygon(points)).extrude(App.Vector(0, 0, thickness))
    fins = []
    for index in range(count):
        fin = base.copy()
        fin.rotate(
            App.Vector(0, 0, 0),
            App.Vector(1, 0, 0),
            360.0 * index / count,
        )
        fins.append(fin)
    return Part.makeCompound(fins)


def aluminum_rail_compound(values):
    n = lambda key: require_number(values, key)
    start = n("aluminum_interface_rail_start_mm")
    length = n("aluminum_interface_rail_length_mm")
    width = n("aluminum_interface_rail_width_mm")
    height = n("aluminum_interface_rail_height_mm")
    radius = n("aluminum_interface_rail_center_radius_mm")
    count = int(n("aluminum_interface_rail_count"))
    base = Part.makeBox(
        length,
        width,
        height,
        App.Vector(start, -width / 2.0, radius - height / 2.0),
    )
    rails = []
    for index in range(count):
        rail = base.copy()
        rail.rotate(
            App.Vector(0, 0, 0),
            App.Vector(1, 0, 0),
            360.0 * index / count,
        )
        rails.append(rail)
    return Part.makeCompound(rails)


def portable_path(path: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def build_document(
    parameters_path: Path,
    fcstd_path: Path,
    step_path: Path,
    report_path: Path,
):
    values, records = load_parameters(parameters_path)
    n = lambda key: require_number(values, key)
    fit = check_fit(parameters_path)
    if fit["overall_status"] == "fail":
        failed = [c["id"] for c in fit["checks"] if c["status"] == "fail"]
        raise RuntimeError(f"Geometry checks failed: {', '.join(failed)}")

    doc = App.newDocument("Andromeda_Packaging_v0_2")
    doc.Label = "Andromeda three-section rocket packaging v0.2"

    metadata = doc.addObject("App::FeaturePython", "Packaging_Metadata")
    metadata.addProperty("App::PropertyString", "ModelRevision", "Traceability")
    metadata.ModelRevision = MODEL_REVISION
    metadata.addProperty("App::PropertyString", "RequirementIDs", "Traceability")
    metadata.RequirementIDs = "SYS-STRUCT-001"
    metadata.addProperty("App::PropertyString", "ParameterSource", "Traceability")
    metadata.ParameterSource = portable_path(parameters_path)
    metadata.addProperty("App::PropertyString", "VerificationStatus", "Traceability")
    metadata.VerificationStatus = fit["overall_status"]
    metadata.addProperty("App::PropertyString", "AxisConvention", "Geometry")
    metadata.AxisConvention = "+X from nose tip toward motor nozzle"
    metadata.addProperty("App::PropertyString", "SectionArchitecture", "Geometry")
    metadata.SectionArchitecture = "nose/recovery | avionics+batteries | motor+fins"
    for record in records:
        property_name = "P_" + "".join(
            character if character.isalnum() else "_" for character in record["key"]
        )
        metadata.addProperty("App::PropertyString", property_name, "Parameters")
        setattr(
            metadata,
            property_name,
            f"{record['value']} {record['unit']} [{record['status']}]",
        )

    sections = doc.addObject("App::DocumentObjectGroup", "Vehicle_Sections")
    interfaces = doc.addObject("App::DocumentObjectGroup", "Section_Interfaces")
    disks = doc.addObject("App::DocumentObjectGroup", "Flight_Disks_Nose_to_Tail")
    equipment = doc.addObject("App::DocumentObjectGroup", "Equipment_Envelopes")
    recovery = doc.addObject("App::DocumentObjectGroup", "Recovery_Envelopes")
    propulsion = doc.addObject("App::DocumentObjectGroup", "Motor_And_Fins")

    od = n("airframe_outer_diameter_mm")
    nominal_id = n("airframe_nominal_inner_diameter_mm")
    outer_radius = od / 2.0
    inner_radius = nominal_id / 2.0
    nose_length = n("nose_ogive_length_mm")
    avionics_start = n("separation_interface_station_mm")
    motor_start = n("motor_interface_station_mm")
    body_end = n("overall_vehicle_length_mm")
    antenna_start = n("antenna_bay_start_mm")
    antenna_length = n("antenna_bay_total_length_mm")
    antenna_gap = n("antenna_bay_gap_mm")
    antenna_zone_length = (antenna_length - antenna_gap) / 2.0

    export_objects = []
    export_objects.append(
        add_shape(
            doc,
            sections,
            "Nose_Recovery_Section",
            "SECTION 1 - Von Karman nose / recovery shell",
            von_karman_solid(
                nose_length,
                outer_radius,
                n("nose_wall_thickness_mm"),
            ),
            (0.88, 0.42, 0.16),
            transparency=68,
        )
    )
    export_objects.append(
        add_shape(
            doc,
            sections,
            "Avionics_Section",
            "SECTION 2 - avionics and batteries shell",
            cylindrical_shell(
                avionics_start,
                antenna_start - avionics_start,
                outer_radius,
                inner_radius,
            ),
            (0.56, 0.66, 0.78),
            transparency=78,
        )
    )
    export_objects.append(
        add_shape(
            doc,
            sections,
            "Upper_Antenna_Bay",
            "SECTION 2 - upper fiberglass antenna bay",
            cylindrical_shell(
                antenna_start,
                antenna_zone_length,
                outer_radius,
                inner_radius,
            ),
            (0.25, 0.82, 0.88),
            transparency=55,
        )
    )
    export_objects.append(
        add_shape(
            doc,
            sections,
            "Antenna_Bay_Spacer",
            "SECTION 2 - fiberglass antenna-bay spacer",
            cylindrical_shell(
                antenna_start + antenna_zone_length,
                antenna_gap,
                outer_radius,
                inner_radius,
            ),
            (0.35, 0.62, 0.68),
            transparency=55,
        )
    )
    export_objects.append(
        add_shape(
            doc,
            sections,
            "Lower_Antenna_Bay",
            "SECTION 2 - lower fiberglass antenna bay",
            cylindrical_shell(
                antenna_start + antenna_zone_length + antenna_gap,
                antenna_zone_length,
                outer_radius,
                inner_radius,
            ),
            (0.25, 0.82, 0.88),
            transparency=55,
        )
    )
    export_objects.append(
        add_shape(
            doc,
            sections,
            "Motor_Section",
            "SECTION 3 - motor and fin shell",
            cylindrical_shell(
                motor_start,
                n("motor_section_length_mm"),
                outer_radius,
                inner_radius,
            ),
            (0.46, 0.48, 0.52),
            transparency=72,
        )
    )

    separation_length = n("nose_shoulder_length_mm")
    separation_outer = n("nose_shoulder_radius_mm")
    separation_inner = n("separation_module_inner_diameter_mm") / 2.0
    export_objects.append(
        add_shape(
            doc,
            interfaces,
            "Separation_Module",
            "INTERFACE 1-2 - 80 mm separation module allocation",
            cylindrical_shell(
                avionics_start,
                separation_length,
                separation_outer,
                separation_inner,
            ),
            (0.92, 0.70, 0.18),
            transparency=20,
        )
    )
    export_objects.append(
        add_shape(
            doc,
            interfaces,
            "Aluminum_Interface_Rails",
            "INTERFACE 2-3 - interrupted internal aluminum load rails",
            aluminum_rail_compound(values),
            (0.72, 0.74, 0.78),
        )
    )

    disk_od = n("flight_disk_outer_diameter_mm")
    disk_thickness = n("flight_disk_thickness_mm")
    axis = App.Vector(1, 0, 0)
    disk_specs = (
        ("Recovery_Control_Disk", "01 Recovery controller disk", "recovery_control_disk_station_mm", (0.86, 0.18, 0.18)),
        ("Recovery_Power_Disk", "02 Recovery power / isolation disk", "recovery_power_disk_station_mm", (0.96, 0.40, 0.16)),
        ("Avionics_Power_Disk", "03 Avionics power-distribution disk", "avionics_power_disk_station_mm", (0.95, 0.72, 0.16)),
        ("Camera_Disk", "04 Four-camera disk", "camera_disk_station_mm", (0.22, 0.52, 0.92)),
        ("Compute_Disk", "05 K26 compute disk", "compute_disk_station_mm", (0.18, 0.72, 0.38)),
        ("Sensor_Disk", "06 Navigation and sensor disk", "sensor_disk_station_mm", (0.66, 0.35, 0.82)),
        ("RF_Disk", "07 PlutoSDR support / RF disk", "rf_disk_station_mm", (0.15, 0.66, 0.78)),
    )
    for name, label, station_key, color in disk_specs:
        station = n(station_key)
        shape = Part.makeCylinder(
            disk_od / 2.0,
            disk_thickness,
            App.Vector(station - disk_thickness / 2.0, 0, 0),
            axis,
        )
        export_objects.append(add_shape(doc, disks, name, label, shape, color))

    battery = Part.makeCylinder(
        n("battery_bay_diameter_mm") / 2.0,
        n("battery_bay_length_mm"),
        App.Vector(n("battery_bay_start_mm"), 0, 0),
        axis,
    )
    export_objects.append(
        add_shape(
            doc,
            equipment,
            "Battery_Bay_Allocation",
            "Battery bay allocation - cells and restraints TBD",
            battery,
            (0.32, 0.32, 0.36),
            transparency=45,
        )
    )

    compute_station = n("compute_disk_station_mm")
    k26 = centered_box(
        compute_station - n("k26_height_mm") / 2.0,
        n("k26_height_mm"),
        n("k26_length_mm"),
        n("k26_width_mm"),
    )
    export_objects.append(
        add_shape(
            doc,
            equipment,
            "K26_SOM_Envelope",
            "K26 SOM published bounding envelope",
            k26,
            (0.10, 0.48, 0.22),
        )
    )

    pluto = centered_box(
        n("pluto_axial_start_mm"),
        n("pluto_enclosure_length_mm"),
        n("pluto_enclosure_width_mm"),
        n("pluto_enclosure_height_mm"),
    )
    export_objects.append(
        add_shape(
            doc,
            equipment,
            "PlutoSDR_Envelope",
            "ADALM-PLUTO enclosed longitudinal envelope",
            pluto,
            (0.12, 0.38, 0.88),
        )
    )

    parachute = Part.makeCylinder(
        n("main_parachute_packed_diameter_mm") / 2.0,
        n("main_parachute_packed_length_mm"),
        App.Vector(n("main_parachute_axial_start_mm"), 0, 0),
        axis,
    )
    export_objects.append(
        add_shape(
            doc,
            recovery,
            "Main_Parachute_Trial_Envelope",
            "Main parachute trial envelope - radial conflict OPEN",
            parachute,
            (0.92, 0.08, 0.10),
            transparency=22,
        )
    )

    mount_start = body_end - n("motor_mount_length_mm")
    motor_mount = cylindrical_shell(
        mount_start,
        n("motor_mount_length_mm"),
        n("motor_mount_outer_diameter_mm") / 2.0,
        n("motor_mount_outer_diameter_mm") / 2.0 - n("motor_mount_wall_thickness_mm"),
    )
    export_objects.append(
        add_shape(
            doc,
            propulsion,
            "Motor_Mount",
            "54 mm motor-mount tube",
            motor_mount,
            (0.78, 0.72, 0.50),
            transparency=40,
        )
    )

    motor_aft = body_end + n("pro54_motor_aft_overhang_mm")
    motor_forward = motor_aft - n("pro54_motor_length_mm")
    motor = Part.makeCylinder(
        n("pro54_motor_diameter_mm") / 2.0,
        n("pro54_motor_length_mm"),
        App.Vector(motor_forward, 0, 0),
        axis,
    )
    export_objects.append(
        add_shape(
            doc,
            propulsion,
            "Pro54_K570_Motor",
            "CTI Pro54-5G K570 motor envelope",
            motor,
            (0.80, 0.16, 0.10),
        )
    )

    fin_root_start = body_end - n("fin_aft_clearance_mm") - n("fin_root_chord_mm")
    fins = trapezoidal_fin_compound(
        fin_root_start,
        outer_radius,
        n("fin_root_chord_mm"),
        n("fin_tip_chord_mm"),
        n("fin_sweep_length_mm"),
        n("fin_span_mm"),
        n("fin_thickness_mm"),
        int(n("fin_count")),
    )
    export_objects.append(
        add_shape(
            doc,
            propulsion,
            "Four_Trapezoidal_Fins",
            "Four OpenRocket trapezoidal fins",
            fins,
            (0.82, 0.20, 0.16),
        )
    )

    metadata.addProperty("App::PropertyLength", "DiskDiametralMargin", "Derived")
    metadata.DiskDiametralMargin = nominal_id - disk_od
    metadata.addProperty("App::PropertyLength", "VehicleBodyLength", "Derived")
    metadata.VehicleBodyLength = body_end
    metadata.addProperty("App::PropertyString", "RecoveryConflict", "Derived")
    metadata.RecoveryConflict = "Existing main packed cylinder conflicts with ogive; see fit report"

    doc.recompute()
    fcstd_path.parent.mkdir(parents=True, exist_ok=True)
    step_path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveAs(fcstd_path.as_posix())
    Part.export(export_objects, step_path.as_posix())

    validation_doc = App.newDocument("STEP_Round_Trip_Validation")
    Import.insert(step_path.as_posix(), validation_doc.Name)
    validation_doc.recompute()
    imported_shapes = []
    imported_object_results = {}
    finite_bounds = []
    for obj in validation_doc.Objects:
        if not hasattr(obj, "Shape") or obj.Shape.isNull():
            continue
        shape = obj.Shape
        if not shape.Solids:
            continue
        bounds = shape.BoundBox
        coordinates = (
            bounds.XMin,
            bounds.XMax,
            bounds.YMin,
            bounds.YMax,
            bounds.ZMin,
            bounds.ZMax,
        )
        finite = all(math.isfinite(value) and abs(value) < 1.0e9 for value in coordinates)
        imported_shapes.append(shape)
        if finite:
            finite_bounds.append(bounds)
        imported_object_results[obj.Name] = {
            "shape_valid": bool(shape.isValid()),
            "finite_bounds": finite,
            "shape_type": shape.ShapeType,
        }
    if finite_bounds:
        round_trip_bounds = {
            "x_length": round(max(b.XMax for b in finite_bounds) - min(b.XMin for b in finite_bounds), 6),
            "y_length": round(max(b.YMax for b in finite_bounds) - min(b.YMin for b in finite_bounds), 6),
            "z_length": round(max(b.ZMax for b in finite_bounds) - min(b.ZMin for b in finite_bounds), 6),
        }
    else:
        round_trip_bounds = None
    all_imported_valid = bool(imported_shapes) and all(shape.isValid() for shape in imported_shapes)
    all_imported_finite = len(finite_bounds) == len(imported_shapes)
    step_round_trip = {
        "object_count": len(imported_shapes),
        "bounded_object_count": len(finite_bounds),
        "all_shapes_valid": all_imported_valid,
        "all_bounds_finite": all_imported_finite,
        "bounding_box_mm": round_trip_bounds,
        "objects": imported_object_results,
    }
    App.closeDocument(validation_doc.Name)

    object_results = {}
    for obj in export_objects:
        bounds = obj.Shape.BoundBox
        object_results[obj.Name] = {
            "shape_valid": bool(obj.Shape.isValid()),
            "solid_count": len(obj.Shape.Solids),
            "bounding_box_mm": {
                "x_length": round(bounds.XLength, 6),
                "y_length": round(bounds.YLength, 6),
                "z_length": round(bounds.ZLength, 6),
                "x_min": round(bounds.XMin, 6),
                "x_max": round(bounds.XMax, 6),
            },
        }
    all_shapes_valid = all(item["shape_valid"] for item in object_results.values())
    overall_pass = all_shapes_valid and all_imported_valid and all_imported_finite
    build_report = {
        "schema_version": 1,
        "tool": {
            "name": "FreeCAD",
            "version": ".".join(str(item) for item in App.Version()[:3]),
        },
        "model_revision": MODEL_REVISION,
        "requirement_ids": ["SYS-STRUCT-001"],
        "fit_check_status": fit["overall_status"],
        "all_exported_shapes_valid": all_shapes_valid,
        "step_round_trip": step_round_trip,
        "objects": object_results,
        "outputs": {
            "fcstd": {
                "path": portable_path(fcstd_path),
                "sha256": sha256(fcstd_path),
                "bytes": fcstd_path.stat().st_size,
            },
            "step": {
                "path": portable_path(step_path),
                "sha256": sha256(step_path),
                "bytes": step_path.stat().st_size,
            },
        },
        "overall_status": "pass" if overall_pass else "fail",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(build_report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return doc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parameters", type=Path, default=PACKAGE_ROOT / "parameters.csv")
    parser.add_argument(
        "--fcstd",
        type=Path,
        default=PACKAGE_ROOT / "exports" / "andromeda-packaging-v0.2.FCStd",
    )
    parser.add_argument(
        "--step",
        type=Path,
        default=PACKAGE_ROOT / "exports" / "andromeda-packaging-v0.2.step",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=PACKAGE_ROOT / "evidence" / "freecad-build-report.json",
    )
    args, _unknown = parser.parse_known_args()
    build_document(
        args.parameters.resolve(),
        args.fcstd.resolve(),
        args.step.resolve(),
        args.report.resolve(),
    )
    return 0


# FreeCAD opens a command-line Python file as a module rather than assigning the
# conventional __main__ name. This is an executable model source.
raise SystemExit(main())
