# Andromeda OpenRocket model v0.2

This model synchronizes OpenRocket with mechanical packaging revision v0.2 while
preserving the v0.1 external mold line and flight-driving inputs.

## Three-section architecture

| Mechanical section | OpenRocket representation | Global interval |
| --- | --- | ---: |
| 1 — nose / recovery | 550 mm Von Kármán nose containing the main and drogue simulation components | 0–550 mm |
| 2 — avionics / batteries | 800 mm carbon-fiber avionics tube plus 200 mm fiberglass RF antenna bay | 550–1550 mm |
| 3 — motor / fins | 600 mm propulsion tube with the Pro54 mount, K570 motor and four fins | 1550–2150 mm |

The 200 mm fiberglass bay is part of section 2, not a fourth separable vehicle
section. Internal aluminum interface rails are packaging/load-path features and
are not represented aerodynamically in OpenRocket.

The upper rail-button global station remains 900 mm from the nose. The lower
rail button, motor, fins, 120 mm body diameter, 2.15 m body length, stage mass/CG
override, recovery deployment events and parachute aerodynamic inputs are carried
over unchanged from v0.1.

## Recovery-model limitation

Both parachutes remain in the OpenRocket model because they are required for the
recovery simulation. Their hierarchy now places them in the ogive, matching the
selected architecture, but this is not proof of mechanical fit:

- the main uses the existing 104 × 180 mm cylindrical pack at x=370–550 mm;
- the mechanical fit checker reports a 2.749 mm radial conflict at its forward
  station;
- the drogue trial station is x=210–370 mm, but its pack, lines, harness and
  deployment free volume remain mechanically unverified.

The simulation component positions must not be treated as a released recovery
installation.

## Files and generation

- `rocket.ork` is the readable OpenRocket XML source.
- `../Andromeda-v0.2.ork` is the packaged file to open in OpenRocket 24.12.
- `Pro54-5G-K570.eng` preserves the reference thrust curve.
- `build_model.py` deterministically transforms v0.1 into v0.2 and packages it.
- `evidence/model-build-report.json` checks the XML/package payload and component
  hierarchy.
- `evidence/mechanical-simulation-impact-report.json` compares fourteen
  flight-driving input groups with v0.1 under rule `XDOM-MECH-SIM-001`.

Regenerate from the repository root:

```bash
python3 simulations/openrocket/andromeda-v0.2/build_model.py
```

The embedded simulation is intentionally marked `notsimulated`. The mechanical
change-impact report establishes flight-input equivalence for this regrouping;
it does not turn historical v0.1 results into v0.2 verification evidence. Rerun
OpenRocket when mass, CG, external geometry, fin geometry, motor, recovery drag or
deployment settings change.
