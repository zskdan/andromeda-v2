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

## Deliverable minimum

Each integration-ready deliverable must identify its ID, revision, owner, requirements, inputs, outputs, interfaces, budgets, evidence, verification result, tool versions, and open issues. Use `integration/manifests/example-deliverable.yaml` as the starting form.

## Safety

Treat hardware programming, RF transmission, launch operations, energetic systems, and destructive tests as approval-gated activities. A controller task is not permission to perform a hazardous action. Keep the v0.2 controller on a trusted network because it has no authentication or TLS.
