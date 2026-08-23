# Andromeda Flight View

Andromeda Flight View is a dependency-free, read-only ground display for
simulation, recorded-flight replay, hardware-in-the-loop testing, and live
telemetry. All sources use the v1 frame defined by
`schema/telemetry-frame.schema.json` and `ICD-TC-GUI-001`.

The display includes a procedural WebGL vehicle model, mission time and phase,
altitude AGL, velocity and acceleration, attitude validity and data age, local
ground track, events, warnings, link statistics, avionics health, video state,
and recording state. No vehicle-command controls are exposed by this MVP.

## Display demonstration

The built-in source is deterministic synthetic data for exercising the GUI. It
is visibly marked `SYNTHETIC` and is not a validated trajectory or flight
evidence.

```bash
python3 -m ground_station.server --mode demo
```

Open `http://127.0.0.1:8765`.

## Simulation or recorded-flight replay

Export newline-delimited JSON in the v1 frame shape, or replay a recording made
by the server. Recorder lines contain `ground_receive_timestamp` and `frame`;
plain frame-per-line files are also accepted.

```bash
python3 -m ground_station.server \
  --mode replay \
  --replay evidence/mission.ndjson \
  --replay-speed 1.0
```

An OpenRocket, RocketPy, or hardware-in-the-loop adapter should translate its
authoritative output into the same v1 frame rather than adding display-specific
logic to the GUI.

## Live telemetry

Live mode accepts a validated JSON frame at `POST /api/telemetry`. Recording is
mandatory unless the explicit bench-test override is used.

```bash
python3 -m ground_station.server \
  --mode live \
  --record evidence/flight-001-ground.ndjson
```

The RF decoder/receiver bridge is still `TBD`; it is responsible for decoding
the radio packet and posting the corresponding v1 frame locally. The server has
no authentication, authorization, or TLS. It binds to loopback by default and
requires `--allow-remote` for a non-loopback address; remote deployment is only
appropriate on an approved trusted private ground network.

## HTTP surface

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/health` | Service and telemetry counters |
| `GET` | `/api/state` | Latest display state |
| `GET` | `/api/stream` | Server-sent telemetry state events |
| `POST` | `/api/telemetry` | Validate, record, and publish one frame |

## Status

This revision is implemented and software-tested, but it is not flight
validated. Update rate, maximum display latency, stale indication latency,
time-alignment error, RF adapter, recording durability, and navigation/attitude
accuracy allocations remain `TBD`. A hardware-in-the-loop test and a complete
ground-segment test are required before operational use.
