# OpenRocket preliminary result — v0.1

Run with OpenRocket 24.12 on 2026-08-20. This is a sizing result, not a flight
readiness prediction.

The external airframe was subsequently divided directly in the `.ork` XML into
550 mm recovery, 250 mm avionics, 200 mm power, and 600 mm propulsion modules.
The drogue was also increased from 0.55 m to a provisional 1.40 m to target no
more than 10.0 m/s at main deployment. OpenRocket was not launched or rerun for
these data-only edits, and the stale embedded flight result was removed. The
historical result below predates the drogue change and is retained only for
traceability; the current terminal-only RocketPy result is authoritative for
the preliminary recovery sizing.

## Current RocketPy recovery sizing

| Quantity | Result |
|---|---:|
| Drogue diameter | 1.40 m |
| Main deployment velocity | 9.60 m/s |
| Main deployment limit | 10.00 m/s |
| Main deployment altitude | 400 m AGL |
| Ground impact velocity | 7.26 m/s |
| Total flight time | 254.19 s |
| Nominal impact distance in 5 m/s wind | 840.75 m |

This is a preliminary analysis pass, not verification. The drogue Cd, packed
volume and mass, opening loads, and wind-dispersion envelope remain unresolved.

## Historical OpenRocket case

- Pro54-5G / CTI 2060K570 Classic motor
- 2.15 m length and 120 mm maximum diameter
- 7.055 kg OpenRocket launch mass (see motor-mass discrepancy below)
- provisional dry CG: 1.280 m from the nose
- 4 m vertical rail
- ISA atmosphere at 200 m launch elevation
- 5 m/s average wind with 0.5 m/s standard deviation
- 0.55 m drogue at apogee
- 1.55 m main at 400 m AGL

## OpenRocket output

| Quantity | Result |
|---|---:|
| Static stability at launch | 2.39 calibres |
| CG at launch | 1.433 m from nose |
| CP at launch | 1.720 m from nose |
| Rail-exit velocity | 30.21 m/s |
| Apogee | 1,857 m AGL |
| Maximum velocity | 235.56 m/s |
| Maximum Mach number | 0.699 |
| Maximum acceleration | 117.80 m/s² (12.0 g) |
| Time to apogee | 18.46 s |
| Total flight time | 144.98 s |
| Main deployment velocity | 21.25 m/s |
| Ground impact velocity | 8.82 m/s |

## Findings

- The preliminary 2.39-calibre stability is inside the adopted 2–6 calibre
  reference range.
- Rail exit is comfortably above the 20 m/s reference criterion.
- The K570 case remains subsonic and does not satisfy an actual Mach 1 mission.
- OpenRocket warns that the main deploys at high speed. The 0.55 m drogue gives
  approximately 21.3 m/s at main deployment; a larger drogue, reefing, or a
  recovery-load design explicitly qualified for that opening speed is needed.
- The 8.82 m/s landing speed is inside the provisional 5–15 m/s recovery target.

## Model limitations

The bundled OpenRocket K570 record contributes 1.735 kg, while the Planete
Sciences Barasinga handbook specifies 1.68 kg. Therefore, the current run is
7.055 kg instead of exactly 7.000 kg. The archived `.eng` curve integrates to
2,058.4 Ns, close to the handbook's 2,062 Ns, and carries the handbook masses.

The dry CG, component packaging, parachute drag coefficients, fin stiffness,
surface finish, launch elevation, and UAE atmospheric profile are provisional.
