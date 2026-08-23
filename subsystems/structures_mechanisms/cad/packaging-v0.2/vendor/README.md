# Vendor geometry

Vendor CAD is intentionally not copied into this directory until its redistribution
terms and exact hardware revision are recorded. The FreeCAD source therefore
uses published rectangular equipment envelopes.

## ADALM-PLUTO

- Official hardware page:
  <https://wiki.analog.com/university/tools/pluto/hacking/hardware>
- Official Rev-B model archive:
  <https://wiki.analog.com/_media/university/tools/pluto/hacking/pluto_revb_3d.zip>
- Archive SHA-256 observed during the initial packaging study:
  `ba36c6c15f76f00fbc288600e2a902973c8033e9ddb986b12cd3ad9e291350fc`
- STEP SHA-256 observed during the initial packaging study:
  `d4be22174c9d02c4d44bf50a2f1dd345be8d8ff0f60b98a3bda88ef5f0bb6407`

The exact STEP model should be used later to check connector protrusion and the
bare-board mounting option. Do not substitute a mesh model for fit verification.

## AMD Kria K26 SOM

- Mechanical dimensions:
  <https://docs.amd.com/r/en-US/ds987-k26-som/K26-SOM-Mechanical-Dimensions>

The model uses the published `77 x 60 x 10.9 mm` envelope. Add the exact
production-SOM model and carrier connector geometry before mounting design begins.
