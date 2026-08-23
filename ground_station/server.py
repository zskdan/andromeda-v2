#!/usr/bin/env python3
"""Dependency-free telemetry ingest, recording, replay, and display server."""

from __future__ import annotations

import argparse
import json
import math
import mimetypes
import sys
import threading
import time
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit


PACKAGE_ROOT = Path(__file__).resolve().parent
WEB_ROOT = PACKAGE_ROOT / "web"
MAX_FRAME_BYTES = 1_048_576


class FrameValidationError(ValueError):
    """Raised when a telemetry frame violates the display interface."""


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FrameValidationError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise FrameValidationError(f"{name} must be finite")
    return result


def _vector(value: Any, name: str, axes: tuple[str, str, str]) -> dict[str, float]:
    if not isinstance(value, dict):
        raise FrameValidationError(f"{name} must be an object")
    return {axis: _finite(value.get(axis), f"{name}.{axis}") for axis in axes}


def _parse_source_timestamp(frame: dict[str, Any]) -> float:
    if "timestamp_unix_ms" in frame:
        return _finite(frame["timestamp_unix_ms"], "timestamp_unix_ms") / 1000.0
    value = frame.get("timestamp")
    if not isinstance(value, str):
        raise FrameValidationError("timestamp or timestamp_unix_ms is required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise FrameValidationError("timestamp must be ISO-8601") from error
    if parsed.tzinfo is None:
        raise FrameValidationError("timestamp must include a UTC offset")
    return parsed.timestamp()


def validate_frame(candidate: Any) -> dict[str, Any]:
    """Validate a v1 frame while preserving unknown forward-compatible fields."""
    if not isinstance(candidate, dict):
        raise FrameValidationError("telemetry frame must be a JSON object")
    frame = dict(candidate)
    if frame.get("schema_version") != 1:
        raise FrameValidationError("schema_version must equal 1")
    sequence = frame.get("sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise FrameValidationError("sequence must be a non-negative integer")
    frame["_source_timestamp_unix_s"] = _parse_source_timestamp(frame)
    frame["mission_time_s"] = _finite(frame.get("mission_time_s"), "mission_time_s")
    if not isinstance(frame.get("phase"), str) or not frame["phase"].strip():
        raise FrameValidationError("phase must be a non-empty string")
    if not isinstance(frame.get("source"), (str, dict)):
        raise FrameValidationError("source must be a string or object")

    attitude = frame.get("attitude")
    if not isinstance(attitude, dict) or not isinstance(attitude.get("valid"), bool):
        raise FrameValidationError("attitude.valid must be Boolean")
    quaternion = attitude.get("quaternion")
    if isinstance(quaternion, list) and len(quaternion) == 4:
        quaternion = dict(zip(("w", "x", "y", "z"), quaternion, strict=True))
    quaternion = _vector(quaternion, "attitude.quaternion", ("w", "x", "y")) | {
        "z": _finite(quaternion.get("z") if isinstance(quaternion, dict) else None,
                     "attitude.quaternion.z")
    }
    norm = math.sqrt(sum(value * value for value in quaternion.values()))
    if norm < 1e-9:
        raise FrameValidationError("attitude.quaternion has zero norm")
    attitude = dict(attitude)
    attitude["quaternion"] = {key: value / norm for key, value in quaternion.items()}
    frame["attitude"] = attitude

    position = frame.get("position")
    if not isinstance(position, dict) or not isinstance(position.get("valid"), bool):
        raise FrameValidationError("position.valid must be Boolean")
    position = dict(position)
    position["latitude_deg"] = _finite(position.get("latitude_deg"), "position.latitude_deg")
    position["longitude_deg"] = _finite(position.get("longitude_deg"), "position.longitude_deg")
    position["altitude_m"] = _finite(position.get("altitude_m"), "position.altitude_m")
    if not -90.0 <= position["latitude_deg"] <= 90.0:
        raise FrameValidationError("position.latitude_deg is outside [-90, 90]")
    if not -180.0 <= position["longitude_deg"] <= 180.0:
        raise FrameValidationError("position.longitude_deg is outside [-180, 180]")
    frame["position"] = position

    optional_vectors = {
        "velocity_ned_m_s": ("north", "east", "down"),
        "acceleration_body_m_s2": ("x", "y", "z"),
        "angular_rate_body_rad_s": ("x", "y", "z"),
    }
    for field, axes in optional_vectors.items():
        if field in frame:
            frame[field] = _vector(frame[field], field, axes)
    return frame


class TelemetryStore:
    """Thread-safe latest-value cache with counters and lossless NDJSON recording."""

    def __init__(self, mode: str, stale_ms: int = 1000, record_path: Path | None = None):
        self.mode = mode
        self.stale_ms = stale_ms
        self._condition = threading.Condition()
        self._latest: dict[str, Any] | None = None
        self._last_sequence: int | None = None
        self._received_monotonic: float | None = None
        self._revision = 0
        self.received_count = 0
        self.dropped_frames = 0
        self.out_of_order_frames = 0
        self.record_path = record_path
        self._record_handle = None
        if record_path is not None:
            record_path.parent.mkdir(parents=True, exist_ok=True)
            self._record_handle = record_path.open("a", encoding="utf-8", buffering=1)

    @property
    def recording(self) -> bool:
        return self._record_handle is not None

    def publish(self, candidate: Any) -> tuple[dict[str, Any], bool]:
        source_frame = candidate
        frame = validate_frame(candidate)
        received_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with self._condition:
            self.received_count += 1
            sequence = frame["sequence"]
            accepted = self._last_sequence is None or sequence > self._last_sequence
            if self._last_sequence is not None:
                if sequence <= self._last_sequence:
                    self.out_of_order_frames += 1
                elif sequence > self._last_sequence + 1:
                    self.dropped_frames += sequence - self._last_sequence - 1
            if self._record_handle is not None:
                record = {"ground_receive_timestamp": received_utc, "frame": source_frame}
                self._record_handle.write(json.dumps(record, separators=(",", ":")) + "\n")
                self._record_handle.flush()
            if accepted:
                self._latest = frame
                self._last_sequence = sequence
                self._received_monotonic = time.monotonic()
                self._revision += 1
                self._condition.notify_all()
            return self.snapshot_locked(), accepted

    def snapshot_locked(self) -> dict[str, Any]:
        age_ms = None
        if self._received_monotonic is not None:
            age_ms = max(0, round((time.monotonic() - self._received_monotonic) * 1000))
        latest = None
        if self._latest is not None:
            latest = {key: value for key, value in self._latest.items() if not key.startswith("_")}
        return {
            "mode": self.mode,
            "latest": latest,
            "received_count": self.received_count,
            "dropped_frames": self.dropped_frames,
            "out_of_order_frames": self.out_of_order_frames,
            "data_age_ms": age_ms,
            "stale_threshold_ms": self.stale_ms,
            "stale": age_ms is None or age_ms > self.stale_ms,
            "recording": self.recording,
            "record_path": str(self.record_path) if self.record_path else None,
            "revision": self._revision,
        }

    def snapshot(self) -> dict[str, Any]:
        with self._condition:
            return self.snapshot_locked()

    def wait_for_revision(self, revision: int, timeout: float) -> dict[str, Any]:
        with self._condition:
            self._condition.wait_for(lambda: self._revision != revision, timeout=timeout)
            return self.snapshot_locked()

    def close(self) -> None:
        if self._record_handle is not None:
            self._record_handle.close()
            self._record_handle = None


class GroundStationServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address: tuple[str, int], store: TelemetryStore, web_root: Path = WEB_ROOT):
        self.store = store
        self.web_root = web_root.resolve()
        super().__init__(address, GroundStationHandler)


class GroundStationHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: GroundStationServer

    def _json(self, status: HTTPStatus, payload: Any) -> None:
        encoded = json.dumps(payload, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:  # noqa: N802
        path = urlsplit(self.path).path
        if path == "/api/health":
            self._json(HTTPStatus.OK, {"status": "ok", **self.server.store.snapshot()})
            return
        if path == "/api/state":
            self._json(HTTPStatus.OK, self.server.store.snapshot())
            return
        if path == "/api/stream":
            self._stream_events()
            return
        self._static(path)

    def do_POST(self) -> None:  # noqa: N802
        if urlsplit(self.path).path != "/api/telemetry":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            size = 0
        if size <= 0 or size > MAX_FRAME_BYTES:
            self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "invalid_content_length"})
            return
        try:
            candidate = json.loads(self.rfile.read(size))
            state, accepted = self.server.store.publish(candidate)
        except (json.JSONDecodeError, UnicodeDecodeError, FrameValidationError) as error:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid_frame", "detail": str(error)})
            return
        self._json(HTTPStatus.ACCEPTED, {"accepted_for_display": accepted, "state": state})

    def _static(self, requested_path: str) -> None:
        relative = "index.html" if requested_path == "/" else unquote(requested_path).lstrip("/")
        candidate = (self.server.web_root / relative).resolve()
        if self.server.web_root not in candidate.parents and candidate != self.server.web_root:
            self._json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})
            return
        if not candidate.is_file():
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        encoded = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8" if content_type.startswith("text/") else content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)

    def _stream_events(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        revision = -1
        try:
            while True:
                state = self.server.store.wait_for_revision(revision, timeout=5.0)
                revision = state["revision"]
                event = "event: telemetry\ndata: " + json.dumps(state, separators=(",", ":")) + "\n\n"
                self.wfile.write(event.encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write("ground-station: " + format % args + "\n")


def _quaternion_from_euler(roll: float, pitch: float, yaw: float) -> dict[str, float]:
    cr, sr = math.cos(roll / 2), math.sin(roll / 2)
    cp, sp = math.cos(pitch / 2), math.sin(pitch / 2)
    cy, sy = math.cos(yaw / 2), math.sin(yaw / 2)
    return {
        "w": cr * cp * cy + sr * sp * sy,
        "x": sr * cp * cy - cr * sp * sy,
        "y": cr * sp * cy + sr * cp * sy,
        "z": cr * cp * sy - sr * sp * cy,
    }


def demonstration_frame(sequence: int, elapsed: float, launch_lat: float, launch_lon: float) -> dict[str, Any]:
    """Generate synthetic display-test data; this is not a validated flight model."""
    cycle = elapsed % 125.0
    t = max(0.0, cycle - 5.0)
    if cycle < 5:
        phase, altitude, vertical = "PRELAUNCH", 0.0, 0.0
    elif t < 12:
        phase = "ASCENT_POWERED"
        altitude = 3000.0 * (0.5 - 0.5 * math.cos(math.pi * t / 55.0))
        vertical = 3000.0 * 0.5 * math.pi / 55.0 * math.sin(math.pi * t / 55.0)
    elif t < 55:
        phase = "ASCENT_COAST"
        altitude = 3000.0 * (0.5 - 0.5 * math.cos(math.pi * t / 55.0))
        vertical = 3000.0 * 0.5 * math.pi / 55.0 * math.sin(math.pi * t / 55.0)
    elif t < 58:
        phase, altitude, vertical = "RECOVERY_TRANSITION", 3000.0, -4.0
    elif t < 115:
        phase = "DESCENT"
        descent = (t - 58.0) / 57.0
        altitude = 3000.0 * max(0.0, 1.0 - descent)
        vertical = -3000.0 / 57.0
    else:
        phase, altitude, vertical = "LANDED", 0.0, 0.0
    east = 0.55 * t
    north = 0.35 * t + 10.0 * math.sin(t / 11.0)
    lat = launch_lat + north / 111_320.0
    lon_scale = max(1e-6, 111_320.0 * math.cos(math.radians(launch_lat)))
    lon = launch_lon + east / lon_scale
    pitch = math.radians(6.0 * math.sin(t / 13.0))
    yaw = math.atan2(east + 0.1, north + 0.1)
    roll = math.radians((t * 18.0) % 360.0)
    mission_time = cycle - 5.0
    events = []
    for name, event_time in (("LIFTOFF", 0.0), ("BURNOUT", 12.0), ("APOGEE", 55.0),
                             ("RECOVERY_DEPLOYED", 58.0), ("TOUCHDOWN", 115.0)):
        if mission_time >= event_time:
            events.append({"name": name, "mission_time_s": event_time})
    return {
        "schema_version": 1,
        "sequence": sequence,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source": {"type": "synthetic_display_demo", "validated_flight_model": False},
        "mission_time_s": mission_time,
        "phase": phase,
        "attitude": {"valid": True, "quality": "SYNTHETIC", "quaternion": _quaternion_from_euler(roll, pitch, yaw)},
        "angular_rate_body_rad_s": {"x": math.radians(18.0), "y": 0.01, "z": 0.02},
        "position": {"valid": True, "latitude_deg": lat, "longitude_deg": lon, "altitude_m": altitude},
        "velocity_ned_m_s": {"north": 0.35, "east": 0.55, "down": -vertical},
        "acceleration_body_m_s2": {"x": 0.4 * math.sin(t), "y": 0.3 * math.cos(t / 2), "z": 9.81 + (22.0 if phase == "ASCENT_POWERED" else 0.0)},
        "link": {"state": "SIMULATED", "rssi_dbm": -61.0, "packet_rate_hz": 20.0},
        "health": {"overall": "NOMINAL", "bus_voltage_v": 15.7, "board_temperature_c": 37.2,
                   "cpu_load_percent": 31.0, "storage_free_percent": 82.0, "reset_count": 0},
        "video": {"state": "STANDBY" if phase == "PRELAUNCH" else "STREAMING"},
        "command": {"last_ack": "NONE"},
        "events": events,
        "warnings": ["SYNTHETIC DISPLAY DATA — NOT FLIGHT EVIDENCE"],
    }


def run_demo(store: TelemetryStore, stop: threading.Event, rate_hz: float, launch_lat: float, launch_lon: float) -> None:
    started = time.monotonic()
    sequence = 0
    period = 1.0 / rate_hz
    while not stop.is_set():
        tick = time.monotonic()
        store.publish(demonstration_frame(sequence, tick - started, launch_lat, launch_lon))
        sequence += 1
        stop.wait(max(0.0, period - (time.monotonic() - tick)))


def run_replay(store: TelemetryStore, stop: threading.Event, path: Path, speed: float) -> None:
    previous_time = None
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if stop.is_set() or not line.strip():
                continue
            candidate = json.loads(line)
            frame = candidate.get("frame", candidate)
            current_time = _finite(frame.get("mission_time_s"), "mission_time_s")
            if previous_time is not None:
                stop.wait(max(0.0, current_time - previous_time) / speed)
            store.publish(frame)
            previous_time = current_time


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("demo", "live", "replay"), default="demo")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--record", type=Path, help="append every received frame to this NDJSON file")
    parser.add_argument("--replay", type=Path, help="NDJSON recording used in replay mode")
    parser.add_argument("--replay-speed", type=float, default=1.0)
    parser.add_argument("--demo-rate-hz", type=float, default=20.0)
    parser.add_argument("--launch-lat", type=float, default=0.0)
    parser.add_argument("--launch-lon", type=float, default=0.0)
    parser.add_argument("--stale-ms", type=int, default=1000,
                        help="provisional display threshold; requirement allocation remains TBD")
    parser.add_argument("--allow-unrecorded-live", action="store_true",
                        help="permit live bench testing without an NDJSON recorder")
    parser.add_argument("--allow-remote", action="store_true",
                        help="explicitly permit a non-loopback bind on a trusted private network")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.mode == "replay" and args.replay is None:
        raise SystemExit("--mode replay requires --replay PATH")
    if args.replay_speed <= 0 or args.demo_rate_hz <= 0 or args.stale_ms <= 0:
        raise SystemExit("rates, replay speed, and stale threshold must be positive")
    if args.mode == "live" and args.record is None and not args.allow_unrecorded_live:
        raise SystemExit("live mode requires --record PATH (or --allow-unrecorded-live for bench testing)")
    if args.host not in {"127.0.0.1", "localhost", "::1"} and not args.allow_remote:
        raise SystemExit("non-loopback bind requires --allow-remote; use only on a trusted private network")
    store = TelemetryStore(args.mode, args.stale_ms, args.record)
    stop = threading.Event()
    producer = None
    if args.mode == "demo":
        producer = threading.Thread(target=run_demo, args=(store, stop, args.demo_rate_hz, args.launch_lat, args.launch_lon), daemon=True)
    elif args.mode == "replay":
        producer = threading.Thread(target=run_replay, args=(store, stop, args.replay, args.replay_speed), daemon=True)
    if producer is not None:
        producer.start()
    server = GroundStationServer((args.host, args.port), store)
    print(f"Andromeda Flight View: http://{args.host}:{server.server_port} ({args.mode.upper()})")
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.shutdown()
        server.server_close()
        store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
