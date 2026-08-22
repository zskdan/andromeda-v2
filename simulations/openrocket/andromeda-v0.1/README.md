# Andromeda OpenRocket model v0.1

Preliminary model inputs:

- 2.15 m total length, 120 mm diameter
- 550 mm Von Karman/Haack-series nose
- single-stage modular body: 550 mm recovery, 250 mm avionics, 200 mm
  power, and 600 mm propulsion sections
- 7.00 kg loaded mass target, including the 1.68 kg Pro54-5G motor
- 5.32 kg provisional dry vehicle mass and 1.28 m provisional dry CG
- four 300/120 x 140 mm trapezoidal fins, 5 mm thick
- 4 m rail with two separate hardpoints 800 mm apart, 5 m/s nominal wind,
  200 m provisional launch elevation
- 0.55 m drogue at apogee and 1.55 m main at 400 m AGL

The `.eng` thrust curve is retained beside the model for traceability. OpenRocket
24.12 already contains the same CTI K570 motor digest used by the `.ork` file.
Its bundled motor record has a 1.735 kg loaded mass, so this first run is at
7.055 kg. The Planete Sciences handbook gives 1.68 kg, corresponding to the
project's exact 7.00 kg target with a 5.32 kg vehicle. This 55 g database
difference must be reconciled in the next model revision.

This model is for sizing iteration. Do not treat its results as flight readiness
evidence until measured component masses, CG, fin stiffness, recovery Cd, launch
site atmosphere, and wind profiles replace the provisional values.

The modules are removable airframe sections, not powered stages. The upper rail
button is assigned to a reinforced band on the recovery module and the lower
button to the propulsion module. A launch rod is intentionally not used because
the 7 kg, 120 mm vehicle requires the greater stiffness of a rail.
