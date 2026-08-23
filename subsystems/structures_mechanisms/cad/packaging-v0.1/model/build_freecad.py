#!/usr/bin/env python3
"""Build the Andromeda v0.1 packaging envelope in FreeCAD 1.1 or newer."""

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
except ImportError as exc:  # pragma: no cover - evaluated only by FreeCAD runtime
    raise SystemExit(
        "Run this script with FreeCADCmd/FreeCAD, not the system Python interpreter."
    ) from exc


MODEL_REVISION = "0.1"
HERE = Path(__file__).resolve().parent
PACKAGE_ROOT = HERE.parent
REPO_ROOT = PACKAGE_ROOT.parents[3]
sys.path.insert(0, str(PACKAGE_ROOT / "tools"))

from check_fit import check_fit, load_parameters, require_number, sha256  # noqa: E402


def set_view(obj, color, transparency=0):
    """Apply optional GUI properties without making headless export depend on them."""
    try:
        obj.ViewObject.ShapeColor = color
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
    fit = check_fit(parameters_path)
    if fit["overall_status"] == "fail":
        failed = [c["id"] for c in fit["checks"] if c["status"] == "fail"]
        raise RuntimeError(f"Envelope checks failed: {', '.join(failed)}")

    doc = App.newDocument("Andromeda_Packaging_v0_1")
    doc.Label = "Andromeda packaging envelope v0.1"

    metadata = doc.addObject("App::FeaturePython", "Packaging_Metadata")
    metadata.addProperty("App::PropertyString", "ModelRevision", "Traceability")
    metadata.ModelRevision = MODEL_REVISION
    metadata.addProperty("App::PropertyString", "RequirementIDs", "Traceability")
    metadata.RequirementIDs = "SYS-STRUCT-001"
    metadata.addProperty("App::PropertyString", "ParameterSource", "Traceability")
    metadata.ParameterSource = parameters_path.as_posix()
    metadata.addProperty("App::PropertyString", "VerificationStatus", "Traceability")
    metadata.VerificationStatus = fit["overall_status"]
    metadata.addProperty("App::PropertyString", "AxisConvention", "Geometry")
    metadata.AxisConvention = "+X from recovery-module forward face toward power module"
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

    airframe_group = doc.addObject("App::DocumentObjectGroup", "Airframe_Envelopes")
    disk_group = doc.addObject("App::DocumentObjectGroup", "Flight_Disks")
    equipment_group = doc.addObject("App::DocumentObjectGroup", "Equipment_Envelopes")

    od = require_number(values, "airframe_outer_diameter_mm")
    nominal_id = require_number(values, "airframe_nominal_inner_diameter_mm")
    outer_radius = od / 2.0
    inner_radius = nominal_id / 2.0
    axis = App.Vector(1, 0, 0)

    recovery_length = require_number(values, "recovery_module_length_mm")
    avionics_length = require_number(values, "avionics_module_length_mm")
    power_length = require_number(values, "power_module_length_mm")
    module_specs = (
        ("Recovery_Module", "Recovery module envelope", 0.0, recovery_length, (0.75, 0.75, 0.78)),
        ("Avionics_Module", "Avionics module envelope", recovery_length, avionics_length, (0.65, 0.72, 0.85)),
        ("Power_Module", "Power module envelope", recovery_length + avionics_length, power_length, (0.85, 0.72, 0.55)),
    )
    export_objects = []
    for name, label, x_start, length, color in module_specs:
        outer = Part.makeCylinder(outer_radius, length, App.Vector(x_start, 0, 0), axis)
        inner = Part.makeCylinder(inner_radius, length, App.Vector(x_start, 0, 0), axis)
        shell = outer.cut(inner)
        export_objects.append(
            add_shape(doc, airframe_group, name, label, shell, color, transparency=82)
        )

    disk_od = require_number(values, "flight_disk_outer_diameter_mm")
    disk_thickness = require_number(values, "flight_disk_thickness_mm")
    disk_specs = (
        ("Recovery_Disk", "Recovery controller disk", "recovery_disk_station_mm", (0.85, 0.25, 0.25)),
        ("Camera_Disk", "Four-camera disk", "camera_disk_station_mm", (0.25, 0.55, 0.90)),
        ("Compute_Disk", "K26 compute disk", "compute_disk_station_mm", (0.25, 0.75, 0.45)),
        ("Sensor_Disk", "Navigation and sensor disk", "sensor_disk_station_mm", (0.70, 0.45, 0.85)),
        ("Power_Disk", "Power-distribution disk", "power_disk_station_mm", (0.90, 0.65, 0.20)),
    )
    for name, label, station_key, color in disk_specs:
        station = require_number(values, station_key)
        disk = Part.makeCylinder(
            disk_od / 2.0,
            disk_thickness,
            App.Vector(station - disk_thickness / 2.0, 0, 0),
            axis,
        )
        export_objects.append(add_shape(doc, disk_group, name, label, disk, color))

    compute_station = require_number(values, "compute_disk_station_mm")
    k26_axial = require_number(values, "k26_height_mm")
    k26_y = require_number(values, "k26_length_mm")
    k26_z = require_number(values, "k26_width_mm")
    k26 = centered_box(compute_station - k26_axial / 2.0, k26_axial, k26_y, k26_z)
    export_objects.append(
        add_shape(
            doc,
            equipment_group,
            "K26_SOM_Envelope",
            "K26 SOM published bounding envelope",
            k26,
            (0.15, 0.55, 0.25),
        )
    )

    pluto_start = require_number(values, "pluto_axial_start_mm")
    pluto_x = require_number(values, "pluto_enclosure_length_mm")
    pluto_y = require_number(values, "pluto_enclosure_width_mm")
    pluto_z = require_number(values, "pluto_enclosure_height_mm")
    pluto = centered_box(pluto_start, pluto_x, pluto_y, pluto_z)
    export_objects.append(
        add_shape(
            doc,
            equipment_group,
            "PlutoSDR_Envelope",
            "ADALM-PLUTO enclosure, longitudinal",
            pluto,
            (0.20, 0.45, 0.85),
        )
    )

    disk_clearance = nominal_id - disk_od
    pluto_diagonal = math.hypot(pluto_y, pluto_z)
    metadata.addProperty("App::PropertyLength", "DiskDiametralMargin", "Derived")
    metadata.DiskDiametralMargin = disk_clearance
    metadata.addProperty("App::PropertyLength", "PlutoCrossSectionDiagonal", "Derived")
    metadata.PlutoCrossSectionDiagonal = pluto_diagonal

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
        # STEP import also creates an Origin with infinite datum planes/axes.
        # Validate only imported bodies that contain one or more solids.
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
            "x_length": round(
                max(bounds.XMax for bounds in finite_bounds)
                - min(bounds.XMin for bounds in finite_bounds),
                6,
            ),
            "y_length": round(
                max(bounds.YMax for bounds in finite_bounds)
                - min(bounds.YMin for bounds in finite_bounds),
                6,
            ),
            "z_length": round(
                max(bounds.ZMax for bounds in finite_bounds)
                - min(bounds.ZMin for bounds in finite_bounds),
                6,
            ),
        }
    else:
        round_trip_bounds = None
    all_imported_valid = bool(imported_shapes) and all(
        shape.isValid() for shape in imported_shapes
    )
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
            "bounding_box_mm": {
                "x_length": round(bounds.XLength, 6),
                "y_length": round(bounds.YLength, 6),
                "z_length": round(bounds.ZLength, 6),
                "x_min": round(bounds.XMin, 6),
                "x_max": round(bounds.XMax, 6),
            },
        }
    all_shapes_valid = all(item["shape_valid"] for item in object_results.values())
    overall_pass = (
        all_shapes_valid
        and step_round_trip["all_shapes_valid"]
        and step_round_trip["all_bounds_finite"]
    )
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
    parser.add_argument(
        "--parameters",
        type=Path,
        default=PACKAGE_ROOT / "parameters.csv",
    )
    parser.add_argument(
        "--fcstd",
        type=Path,
        default=PACKAGE_ROOT / "exports" / "andromeda-packaging-v0.1.FCStd",
    )
    parser.add_argument(
        "--step",
        type=Path,
        default=PACKAGE_ROOT / "exports" / "andromeda-packaging-v0.1.step",
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
# conventional ``__main__`` name. This file is an executable model source, not an
# importable library, so invoke the entry point unconditionally.
raise SystemExit(main())
