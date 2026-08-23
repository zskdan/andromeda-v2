# Andromeda packaging envelope v0.1

This is a coarse, parameter-driven mechanical packaging study for the current
Andromeda module geometry. It is not a released airframe, PCB, bracket, or flight
installation design.

## Scope and configuration

The model traces to `SYS-STRUCT-001` and uses the current provisional `120 mm`
outer diameter, `2 mm` design wall, and `116 mm` nominal inner diameter. The
manufactured minimum clear bore remains `TBD`.

The current OpenRocket module lengths are used only as provisional packaging
inputs:

- recovery: `550 mm`
- avionics: `250 mm`
- power: `200 mm`

The local model axis is `+X`, starting at the forward face of the recovery module
and increasing toward the power module.

The conceptual flight arrangement is:

- recovery controller disk in the recovery module;
- camera, K26 compute, and sensor disks in the avionics module;
- ADALM-PLUTO enclosure mounted longitudinally in the avionics module;
- power-distribution disk in the power module;
- breakout disk excluded from the flight assembly.

Disk stations are visualization assumptions, not allocated mechanical interfaces.

## Files

- `parameters.csv` is the Git-readable model input and records the status and source
  of every value.
- `tools/check_fit.py` performs deterministic radial and axial envelope checks.
- `model/build_freecad.py` builds the native FreeCAD document and a neutral STEP
  assembly.
- `evidence/fit-report.json` is generated evidence from the deterministic fit check.
- `vendor/README.md` records official model sources and observed checksums.

## Run the checks

From the repository root:

```bash
python3 subsystems/structures_mechanisms/cad/packaging-v0.1/tools/check_fit.py \
  --parameters subsystems/structures_mechanisms/cad/packaging-v0.1/parameters.csv \
  --output subsystems/structures_mechanisms/cad/packaging-v0.1/evidence/fit-report.json
```

## Build with FreeCAD

FreeCAD 1.1.3 is the current authoring version. From the repository root:

```bash
FreeCADCmd subsystems/structures_mechanisms/cad/packaging-v0.1/model/build_freecad.py
```

The default input and output paths are resolved relative to the model source, so
the command works from any directory. FreeCAD consumes ordinary command-line
options itself; use the defaults for this revision rather than appending script
arguments.

The checked-in `FCStd` and STEP files were generated with FreeCAD 1.1.3. The build
report records source-shape validity, output hashes and a STEP re-import check.
Regenerate the outputs after changing any parameter or model source.

## Intended Onshape migration

The public Onshape integration should use a versioned STEP export as its geometry
snapshot and `parameters.csv` as the parameter handoff. STEP import does not carry
the FreeCAD feature history, so rebuild the airframe, module boundaries, disks, and
keep-out volumes as native Onshape features and use the imported STEP only as a
reference/check.

At the migration point:

1. freeze a FreeCAD revision and generate its fit report;
2. export STEP, not STL;
3. create a matching Onshape document version;
4. reproduce the parameter table as Onshape variables;
5. compare mass properties, bounding boxes, and critical clearances;
6. record the Onshape version URL and comparison evidence in the manifest.

## Not yet modeled

- manufactured bore, ovality, couplers, fasteners and airframe intrusions;
- tie rods, rails, brackets and vibration isolators;
- USB and coax cable bend radii or connector service access;
- camera bodies, optical windows and structural window reinforcement;
- sensor ports, recovery actuator, battery and power components;
- local DC/DC converters, fuses, stack connectors and edge LEDs;
- thermal paths, flight loads, vibration, shock and assembly sequence.

Consequently, a current `provisional_pass` means only that the simple published
envelopes do not violate the nominal cylindrical and axial boundaries.
