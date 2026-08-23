# Andromeda engineering-agent contract

The committed repository is authoritative. Do not treat chat memory as project state when a requirement, interface, decision, manifest, test result, or status record exists in the repository.

## Organization

- `architect` owns system architecture, requirement allocation, budgets, interfaces, and trade decisions.
- End-to-end subsystem owners (`rf_system`, `video_system`, `telemetry_command`, `structures_mechanisms`) own behavior across vehicle and ground segments.
- Segment-specific owners such as `flight_dynamics` own their bounded domain.
- Specialists (`electronics`, `fpga`, `software`, `mechanical`, `test`) provide implementation expertise; they do not silently change system architecture.
- `integrator` independently checks requirement evidence, interfaces, budgets, and verification completeness.

The architect delegates by engineering capability, not by machine name. Runtime tasks declare `required_capabilities` and `required_resource_types`; the controller chooses the worker.

## Required engineering behavior

1. Identify the requirement IDs and authoritative inputs before implementation.
2. Record assumptions and unresolved values explicitly as `TBD` or an issue; do not invent measurements.
3. Use deterministic engineering tools for calculations and simulations where practical.
4. Keep generated evidence traceable to commands, tool versions, inputs, and requirement IDs.
5. Publish a manifest for any deliverable intended for integration.
6. Distinguish implemented, verified, and validated. An agent assertion is not verification evidence.
7. Escalate cross-domain trades to the architect. The integrator detects and quantifies conflicts; it does not make architectural trades silently.
8. Do not blindly retry engineering failures. Automatic retries are for infrastructure loss only.
9. Evaluate every change against `integration/change-impact-rules.json`, perform every triggered downstream review, and commit its evidence or an explicit evidence-backed no-update disposition.
10. Commit and push every repository modification made by an agent before declaring the task complete. Push to `origin/main` unless the user explicitly selects another branch or says not to push. Stage only the files owned by the task, preserve unrelated working-tree changes, and report a blocked push as incomplete work.

## Mandatory cross-domain change gates

- **Mechanical to simulation (`XDOM-MECH-SIM-001`):** every structures,
  mechanisms, packaging, airframe, recovery-installation, fin, launcher-interface,
  mass, or CG change triggers a flight-dynamics review. Check OpenRocket and
  RocketPy inputs and update and rerun the affected model when a flight-driving
  value changes. If no model update or rerun is required, commit deterministic
  equivalence evidence and the criteria that would require a rerun.
- **Electronics to mechanical (`XDOM-ELEC-MECH-001`):** every electronics
  hardware, PCB, connector, component, cable, antenna, power-dissipation, or
  sensor-interface change triggers a structures/mechanisms review. Check and
  update packaging CAD, keep-outs, mass/CG allocation, mounting, thermal path,
  assembly access, and interface records whenever affected. If no mechanical
  update is required, commit the reviewed revision and clearance evidence.

An unsupported statement that a downstream domain is unaffected is not evidence.
Use `python3 scripts/check_change_impact.py --working-tree` before committing and
`python3 scripts/check_change_impact.py --base HEAD~1 --head HEAD` after committing.
The path triggers are the minimum automatic gate; engineers must also invoke a
rule when semantic impact exists outside the listed paths.

## Deliverable minimum

Each integration-ready deliverable must identify its ID, revision, owner, requirements, inputs, outputs, interfaces, budgets, change-impact dispositions, evidence, verification result, tool versions, and open issues. Use `integration/manifests/example-deliverable.yaml` as the starting form.

## Safety

Treat hardware programming, RF transmission, launch operations, energetic systems, and destructive tests as approval-gated activities. A controller task is not permission to perform a hazardous action. Keep the v0.2 controller on a trusted network because it has no authentication or TLS.
