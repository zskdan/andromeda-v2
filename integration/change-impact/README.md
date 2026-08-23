# Cross-domain change-impact evidence

Use this directory when a rule in `../change-impact-rules.json` is triggered but
the reviewed downstream artifact does not need modification. Updating the actual
downstream model, CAD, interface or manifest is preferred when it is affected.

A no-update record must be YAML and include at least:

```yaml
schema_version: 1
impact_record:
  id: XDOM-IMPACT-YYYY-NNN
  revision: 1
  status: assessed
change:
  description: TBD
  changed_artifacts: []
triggered_rules:
  - id: XDOM-MECH-SIM-001
    review_owner: flight_dynamics
assessment:
  inputs_reviewed: []
  calculations_or_comparisons: []
  affected_requirements: []
  disposition: no_update_required
  rationale: TBD
  update_or_rerun_criteria: []
evidence: []
open_issues: []
```

For `XDOM-ELEC-MECH-001`, the record must identify the exact electronic revision,
PCB/component envelope, mass, mounting, connectors/cables, thermal dissipation,
antenna/sensor/optical constraints, and the mechanical clearances reviewed.

For `XDOM-MECH-SIM-001`, the record must compare geometry, mass/CG, fins, motor,
recovery, launcher and environmental inputs and state whether OpenRocket or
RocketPy must be rerun.
