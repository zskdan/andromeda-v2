# Andromeda Agent Framework v0.2

Andromeda v0.2 is a dependency-free reference control plane for a multidisciplinary rocket engineering agent organization. Git remains the engineering memory; ChatGPT, Codex, or OpenCode can act as human interfaces; an always-on controller holds work; and workers advertise capabilities and physical resources instead of being hard-coded into tasks.

This is a safe starting skeleton, not a production remote-execution service. It has no authentication or TLS. Keep it on localhost or a trusted private network until those controls are added.

## What is included

- persistent JSON task queue and worker registry;
- capability and physical-resource matching;
- `ONLINE` / `SUSPECT` / `OFFLINE` status derived from heartbeats;
- a formal task lifecycle with transition history;
- wait-for-resource and bounded infrastructure retry behavior;
- outbound-polling worker with a command allowlist and no shell interpolation;
- JSON Schemas and example definitions for three initial workers;
- ChatGPT control-console and Codex agent guidance;
- structural, unit, and controller-service end-to-end validation;
- reproducible ZIP and TAR.GZ packaging script.
- offline-capable 3D ground-station visualization with simulation, replay, live
  telemetry ingest, and NDJSON recording (`ground_station/`).

## 3D flight visualization

Run the visibly labelled synthetic display exercise:

```bash
python3 -m ground_station.server --mode demo
```

Then open `http://127.0.0.1:8765`. Simulation/replay and recorded live-ingest
commands, the telemetry contract, operational limitations, and flight-readiness
TBDs are documented in `ground_station/README.md`.

## Quick start

Requires Python 3.11 or newer. No third-party packages are needed.

From the extracted package, open three terminals.

1. Start the controller:

   ```bash
   python3 -m andromeda_control.controller
   ```

2. Start the cloud simulation worker:

   ```bash
   python3 -m andromeda_control.worker \
     --config control/workers/worker3.json
   ```

3. Submit the smoke-test task and inspect status:

   ```bash
   python3 -m andromeda_control.cli_submit control/tasks/example-flight-simulation.json
   python3 -m andromeda_control.cli_status
   ```

The installed console equivalents are `andromeda-controller`, `andromeda-worker`, `andromeda-submit`, and `andromeda-status`. To install them in a virtual environment, run `python3 -m pip install -e .`.

## Recommended startup sequence

1. Extract v0.2 and commit it to a new Git repository.
2. Run `python3 scripts/validate.py`.
3. Start the controller locally.
4. Edit `control/workers/worker3.json` to describe the actual cloud station, then start that worker.
5. Submit the included flight-simulation smoke test and confirm it reaches `SUCCEEDED`.
6. Replace the smoke command with a real RocketPy or OpenRocket script.
7. Configure and connect `worker1` and `worker2`.
8. Stop `worker1`, submit the Vivado example, and confirm `WAITING_FOR_RESOURCE`.
9. Restart `worker1` and confirm automatic dispatch.
10. After local testing, put the controller behind authentication, TLS, and a private network on an always-on host.
11. Integrate openEMS, FreeCAD, KiCad, Vivado, ZCU102, and PlutoSDR one at a time.

Do not list a capability until it is genuinely installed and tested. The `configure-me` version strings in the examples are placeholders.

## Task lifecycle

```text
SUBMITTED -> QUEUED -> READY -> DISPATCHED -> RUNNING -> SUCCEEDED
                 |                                  \-> FAILED
                 \-> WAITING_FOR_RESOURCE -> READY

DISPATCHED/RUNNING -- infrastructure loss --> RETRY_WAIT -> QUEUED
any non-terminal state -------------------------------> CANCELLED
```

Resource absence waits indefinitely. Worker loss is retried a bounded number of times. A command or engineering verification failure is not blindly retried; it returns to its owner for analysis.

## API summary

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Liveness and counts |
| `GET` | `/v1/workers` | Worker registry and derived status |
| `POST` | `/v1/workers/register` | Register or refresh worker definition |
| `POST` | `/v1/workers/{id}/heartbeat` | Declare worker alive and refresh properties |
| `POST` | `/v1/workers/{id}/claim` | Claim one dispatched job |
| `GET` | `/v1/tasks` | List tasks |
| `GET` | `/v1/tasks/{id}` | Inspect a task and history |
| `POST` | `/v1/tasks` | Submit a task |
| `POST` | `/v1/tasks/{id}/cancel` | Cancel a non-terminal task |
| `POST` | `/v1/workers/{wid}/tasks/{tid}/complete` | Return success |
| `POST` | `/v1/workers/{wid}/tasks/{tid}/fail` | Return a failure |

## Repository map

```text
.codex/agents/          named engineering-agent guidance
andromeda_control/      runnable controller, scheduler, worker, clients
control/tasks/          task examples and future queued-task exports
control/workers/        worker configurations
control/resources/      physical resource records
control/schemas/        machine-readable contracts
control/policies/       documented scheduler and retry policy
prompts/                ChatGPT control-console prompt
requirements/           initial requirements and interfaces
subsystems/             subsystem engineering work areas
integration/            manifests and verification records
scripts/                validation and release packaging
tests/                  unit and HTTP end-to-end tests
```

## v0.2 limitations

- one controller process and one JSON state file;
- one task at a time per reference worker;
- capability names match exactly; version constraints are not yet evaluated;
- physical resource reservation is represented but not transactionally leased;
- task artifacts are referenced by path; they are not uploaded;
- no authentication, authorization, TLS, secrets management, or sandbox isolation;
- task cancellation cannot terminate an already running subprocess in this release.

These limits are intentional: v0.2 validates the control-plane model before adding distributed-system complexity.
