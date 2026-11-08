# Battery architecture and sizing decision

- **Status:** Accepted as the prototype design baseline; flight use requires the verification gates below
- **Date:** 2026-08-28
- **Owner:** System architect / electronics
- **Requirements:** `TDO-PWR-001`, `TDO-ISO-001`, `TDO-OPS-001`

## Decision

Andromeda-v2 shall use two electrically isolated battery domains:

1. A **4S 6000 mAh LiPo** main payload battery for the KV260-class SoC on the custom carrier, four cameras, PlutoSDR, 3 W RF power amplifier, storage, and associated conversion losses.
2. A separate **2S 850–1300 mAh LiPo** recovery battery feeding the two recovery servos through a **6 V regulator/BEC rated for at least 10 A peak** and the recovery electronics required for deployment.

The main battery has a nominal voltage of 14.8 V and nominal energy of **88.8 Wh**. For mission planning, only 80% of nominal energy shall be treated as usable: **71.0 Wh**. A representative main-pack mass allocation is **570–625 g** (approximately 600 g). The recovery pack adds approximately **60–110 g**, giving a preliminary total battery mass allocation of **630–735 g**, excluding regulators, protection, wiring, connectors, and mounts.

This decision sizes the batteries; it does not select a specific vendor or flight-qualified part number.

## Basis

The mission requirement is at least **60 minutes of continuous simultaneous operation** of all installed flight avionics under the approved worst-case profile (`TDO-PWR-001`). The sizing case includes:

- KV260-class Zynq UltraScale+ MPSoC on a custom carrier;
- four active cameras;
- PlutoSDR;
- a power amplifier producing 3 W RF output;
- storage and normal peripherals;
- DC/DC conversion losses; and
- two recovery servos on the independent recovery domain.

The current estimate is:

| Case | Main-battery power | Approximate current at 14.8 V |
|---|---:|---:|
| Expected continuous operation | 39–44 W | 2.6–3.0 A |
| Conservative continuous sizing case | 56 W | 3.8 A |
| Transient design allowance | — | 8–10 A peak |

The 3 W RF rating is conducted RF output, not DC input. The PA is provisionally budgeted at **10–15 W electrical input** until its efficiency is measured at the selected operating point.

## Capacity trade

Runtime below uses 80% usable energy and excludes the independent recovery battery.

| Main pack | Nominal energy | Usable energy | Runtime at 56 W | Disposition |
|---|---:|---:|---:|---|
| 4S 4000 mAh | 59.2 Wh | 47.4 Wh | ~51 min | Rejected: does not satisfy 60 minutes |
| 4S 5000 mAh | 74.0 Wh | 59.2 Wh | ~63 min | Minimum only: insufficient practical margin |
| **4S 6000 mAh** | **88.8 Wh** | **71.0 Wh** | **~76 min** | **Selected** |

At the expected 39–44 W load, the selected pack provides approximately **97–109 minutes** from the 80% usable-energy budget. At the 56 W conservative case it provides approximately **76 minutes**, leaving about 16 minutes beyond the 60-minute requirement while preserving the 20% energy derating.

## Rationale

The 4S 6000 mAh pack is selected because it satisfies the conservative one-hour case with useful margin while keeping the preliminary main-pack mass near 600 g. A 5000 mAh pack is technically above one hour only on the present paper estimate and leaves too little allowance for cold temperature, aging, wiring loss, converter variation, manufacturing tolerance, or late load growth.

The recovery battery is separate so that a short circuit, brownout, reset, or load-shedding event in the experimental video/WB payload cannot remove recovery actuation power. This supports `TDO-ISO-001`. The recovery energy calculation is intentionally independent of the one-hour main-payload calculation because the servo load is short-duration and peak-current dominated.

## Power architecture constraints

- The video/WB domain shall be separately fused or protected and shall be load-sheddable before essential telemetry, navigation, recording, and recovery functions.
- The recovery power path shall not depend on the main payload battery, payload DC/DC converters, or payload software remaining operational.
- Main-pack wiring, connector, fuse/protection, and converters shall support at least the 8–10 A transient allowance without an unacceptable voltage dip at the SoC or radio rails.
- The final pack and regulators shall be rated for the measured continuous and transient currents across the qualified temperature range; a nominal C-rating alone is not verification.
- Preflight readiness checks shall report both battery domains independently.

## Assumptions and open values

- The power figures are engineering estimates, not measurements from the final custom board.
- PA consumption assumes 10–15 W DC for 3 W RF output and must be replaced by measured data.
- Main-pack mass is a planning range; the exact pack, enclosure, restraints, cabling, regulators, and protection remain TBD.
- The minimum post-landing NB recovery-beacon duration remains TBD and may require a separate essential-avionics energy allocation or revised load-shedding policy.
- Cold-temperature capacity, cell aging, high-current voltage sag, vibration, shock, and installation thermal behavior are not yet qualified.

## Verification gates before flight

1. Measure average and peak current for every rail and load state on the final custom hardware.
2. Run a full-system endurance test for at least 60 minutes with all required cameras, WB, NB, navigation, and recording active; log pack voltage, rail currents, temperatures, resets, and runtime.
3. Repeat the worst-case test at the minimum qualified battery state of charge and temperature, using an aged or conservatively derated pack as applicable.
4. Exercise simultaneous radio and camera transients and verify that no rail violates its undervoltage limit and no processor, camera, PlutoSDR, or PA resets.
5. Stall or dynamically load both recovery servos in a representative mechanism and verify the recovery battery, BEC, protection, and wiring at the specified peak current.
6. Fault the main payload domain and verify that recovery deployment remains available; fault the video/WB branch and verify that essential telemetry and navigation continue.
7. Weigh the installed battery assemblies and propagate the measured mass and position into the mechanical packaging, center-of-gravity, and flight-dynamics models before design release.

Until these gates pass, **4S 6000 mAh + independent 2S recovery battery is the procurement and packaging baseline, not flight-qualification evidence**.

## Change-impact disposition

This record establishes a planning allocation rather than changing an already released battery assembly. No existing CAD or flight model is modified by this commit. Once a specific pack, protection, regulators, wiring, mounts, mass, and installed position are selected, `XDOM-ELEC-MECH-001` requires a mechanical packaging/interface review; the resulting measured mass and CG contribution then require the applicable `XDOM-MECH-SIM-001` flight-dynamics review and model update.
