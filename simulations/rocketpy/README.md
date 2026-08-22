# Andromeda RocketPy simulation

This model uses the RocketPy virtual environment installed at:

`/home/zakaria/workspace/ai-factory/andromeda-v2/simulation`

Run the nominal case from the repository root:

```bash
MPLCONFIGDIR=/tmp/andromeda-mpl \
  /home/zakaria/workspace/ai-factory/andromeda-v2/simulation/bin/python \
  simulations/rocketpy/andromeda_v01.py
```

The model is terminal-only and does not create plots or screenshots. Results
are written to `andromeda_v01_results.json`.

## Modular airframe layout

The 2.150 m vehicle uses a legacy-inspired modular stack while remaining one
powered stage:

| Module | Tail-to-nose envelope | Length | Provisional mass |
| --- | ---: | ---: | ---: |
| Propulsion | 0.000-0.600 m | 0.600 m | 2.170 kg |
| Power | 0.600-0.800 m | 0.200 m | 0.550 kg |
| Avionics | 0.800-1.050 m | 0.250 m | 0.700 kg |
| Recovery | 1.050-1.600 m | 0.550 m | 1.400 kg |
| Nose | 1.600-2.150 m | 0.550 m | 0.500 kg |

These roll-up masses total 5.320 kg without the motor and produce a provisional
dry CG of approximately 0.870 m forward of the tail. Each allocation includes
the associated airframe, interfaces, and installed hardware; it must eventually
be replaced by a measured component-level mass budget.

The launch guide is a 4 m rail with buttons 0.800 m apart. A rod is not used:
the rail provides substantially better bending stiffness and directional
control for a 7 kg, 120 mm diameter vehicle.

## Requirements traceability

- `SYS-LAUNCH-001`: preliminary 1515-or-equivalent rail interface with two
  buttons; a rod is non-baseline pending equivalent stiffness, fit, clearance,
  and departure-velocity verification.
- `SYS-LAUNCH-002`: the nominal RocketPy result is 25.12 m/s at rail departure,
  above the provisional 20.0 m/s threshold.
- `SYS-MASS-001`: the model is exactly 7.00 kg loaded, but the component masses
  and CG remain allocations rather than measurements.

The mass, CG, inertia, drag curves, motor grain geometry, atmosphere, and
recovery coefficients are preliminary engineering assumptions.
