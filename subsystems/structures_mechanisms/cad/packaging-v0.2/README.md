# Andromeda three-section packaging model v0.2

This revision turns the original cylindrical packaging envelope into a recognizable
rocket while keeping the external geometry traceable to the synchronized OpenRocket
v0.2 model. It remains a preliminary allocation model, not a released airframe,
joint, antenna installation, PCB, recovery deployment system, or motor-retention
design.

## External geometry

The model uses `+X` from the nose tip toward the motor nozzle and preserves the
OpenRocket 2.15 m outer mold line:

| Section | Axial interval | Contents |
| --- | ---: | --- |
| 1 — nose / recovery | 0–550 mm | 550 mm C=0 Haack/Von Kármán ogive and main-parachute trial envelope |
| 2 — avionics / batteries | 550–1550 mm | separation module, recovery electronics, battery bay, avionics disks, K26, PlutoSDR and two fiberglass antenna zones |
| 3 — motor / fins | 1550–2150 mm | 54 mm motor mount, Pro54-5G K570 envelope and four trapezoidal fins |

The straight-body outside diameter is 120 mm. The 2 mm provisional wall gives a
116 mm nominal clear diameter before couplers, fasteners, ovality and local
reinforcement are included.

OpenRocket-derived geometry includes:

- 550 mm Von Kármán ogive;
- 600 mm propulsion section;
- 54 × 488 mm configured Pro54 K570 motor envelope with 10 mm aft overhang;
- four fins with 300 mm root, 120 mm tip, 140 mm sweep, 140 mm span and 5 mm
  thickness.

## Interfaces and stack order

Interface 1–2 is an 80 mm separation-module allocation from x=550 to 630 mm,
using the existing OpenRocket nose-shoulder length as its provisional envelope.

The conceptual disk and bay order from nose to tail is:

1. recovery controller disk at x=650 mm;
2. recovery power/isolation disk at x=695 mm;
3. battery-bay allocation from x=730 to 910 mm;
4. avionics power-distribution disk at x=940 mm;
5. camera disk at x=985 mm;
6. K26 compute disk at x=1030 mm;
7. PlutoSDR support/RF disk at x=1130 mm;
8. longitudinal enclosed PlutoSDR from x=1180 to 1297 mm;
9. complete dual-GNSS INS/navigation disk at x=1320 mm;
10. two 90 mm fiberglass antenna zones from x=1350 to 1440 mm and x=1460
    to 1550 mm, with conceptual GNSS ring-feed stations at x=1395 and 1505 mm.

The INS/navigation disk was moved aft from x=1080 to 1320 mm so both GNSS
receiver modules, the IMU and the navigation processor can share one local
carrier with the environmental/acoustic sensors close to the antenna feeds. The
resulting minimum axial spans from the
disk plane to the two candidate ring-feed centers are 75 and 185 mm; actual coax
routing, bend radii and insertion losses remain TBD. Long communication and
timing links toward the compute disk require a qualified differential physical
layer; raw single-ended UART is not allocated as the vehicle-level interface.

The new station is immediately forward of the RF bay rather than inside it. A
bare 1.6 mm disk has 22.2 mm clearance to the modeled Pluto enclosure and 29.2 mm
to the antenna/rail region. Those values do not establish assembly fit because
the INS component depth, Pluto connector/service volume, mounts and harness bends
are still TBD. The INS disk mass is also TBD, so the physical CG shift cannot yet
be applied to the provisional OpenRocket mass/CG override.

Interface 2–3 is the fiberglass antenna region plus four conceptual 6 × 6 mm
longitudinal aluminum rails running from x=1350 to 1600 mm. The rails cross the
joint but leave open azimuth sectors for RF. A continuous 360-degree aluminum
sleeve is intentionally not modeled because it would shield and detune antennas
installed over it. Rail count, section, attachments and load capacity require
structural sizing; antenna positions require full RF/coexistence analysis.

## Recovery conflict found

The existing OpenRocket main-parachute packed envelope is 104 mm diameter by
180 mm long. When aft-aligned inside the ogive from x=370 to 550 mm, its forward
radius exceeds the provisional ogive inner radius by about 2.75 mm. This is shown
as a red envelope and reported as `PKG-RECOVERY-001: open_conflict`.

That result does not prove the parachute cannot be packaged in the nose: a soft
pack may use a non-cylindrical bag. It does show that the existing cylindrical
OpenRocket packed envelope cannot be transferred into the ogive unchanged. The
drogue parachute, lines, harness, deployment device and required free volume are
still unallocated. Recovery packaging therefore needs a dedicated trade before
this architecture is frozen.

## Files and reproducibility

- `parameters.csv` records every model input, status and source.
- `tools/check_fit.py` performs deterministic radial, axial, interface, motor,
  fin and recovery-envelope checks.
- `tools/check_openrocket_transfer.py` compares 21 external-geometry parameters
  with the committed OpenRocket XML.
- `model/build_freecad.py` generates the native FreeCAD document and STEP export.
- `evidence/fit-report.json` records deterministic calculation evidence.
- `evidence/openrocket-transfer-report.json` records the OpenRocket transfer check.
- `evidence/freecad-build-report.json` records FreeCAD version, object validity,
  hashes and STEP round-trip results.
- `exports/andromeda-packaging-v0.2.FCStd` is the native model.
- `exports/andromeda-packaging-v0.2.step` is the neutral Onshape handoff.

Run the deterministic checks from the repository root:

```bash
python3 subsystems/structures_mechanisms/cad/packaging-v0.2/tools/check_fit.py \
  --parameters subsystems/structures_mechanisms/cad/packaging-v0.2/parameters.csv \
  --output subsystems/structures_mechanisms/cad/packaging-v0.2/evidence/fit-report.json
```

Verify the OpenRocket geometry transfer:

```bash
python3 subsystems/structures_mechanisms/cad/packaging-v0.2/tools/check_openrocket_transfer.py \
  --parameters subsystems/structures_mechanisms/cad/packaging-v0.2/parameters.csv \
  --openrocket simulations/openrocket/andromeda-v0.2/rocket.ork \
  --output subsystems/structures_mechanisms/cad/packaging-v0.2/evidence/openrocket-transfer-report.json
```

Build with FreeCAD 1.1.3:

```bash
FreeCADCmd subsystems/structures_mechanisms/cad/packaging-v0.2/model/build_freecad.py
```

The checked-in FCStd and STEP files are generated outputs. Regenerate them after
changing the CSV or builder and review the new evidence before committing.

## Onshape migration

Import the versioned STEP file into the public Onshape integration document and
rebuild the section shells, interfaces, rails, fins, disks and keep-outs as native
features driven by variables copied from `parameters.csv`. STEP is the geometry
snapshot and comparison reference; it does not preserve FreeCAD feature history.

## Still open

- manufactured clear bore, couplers, fasteners and local reinforcement;
- separation mechanics, harness routing and deployment clearances;
- drogue location and practical main-parachute packing;
- battery selection, restraint, protection, isolation and venting;
- camera bodies, windows and window reinforcement;
- exact Pluto PCB/connectors, USB and coax service volumes and thermal path;
- INS disk component, shield, connector, mounting and harness envelope, mass,
  power dissipation and vibration qualification;
- GNSS coax routed lengths, insertion losses, connector retention and separation
  from Pluto/NB/WB transmit paths;
- antenna elements, polarization, spacing, feed routing and RF interaction with
  the aluminum rails, motor case and other electronics;
- rail load path, joint sizing, fin flutter, motor retention, thermal, vibration,
  shock and assembly sequence.
