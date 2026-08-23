import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from ground_station.server import (
    FrameValidationError,
    GroundStationServer,
    TelemetryStore,
    demonstration_frame,
    validate_frame,
)


class FrameValidationTests(unittest.TestCase):
    def test_valid_frame_is_normalized_and_preserves_extensions(self):
        frame = demonstration_frame(7, 8.0, 48.0, 2.0)
        frame["attitude"]["quaternion"] = {"w": 2.0, "x": 0.0, "y": 0.0, "z": 0.0}
        frame["extension"] = {"future": True}
        validated = validate_frame(frame)
        self.assertEqual(validated["sequence"], 7)
        self.assertEqual(validated["attitude"]["quaternion"]["w"], 1.0)
        self.assertTrue(validated["extension"]["future"])

    def test_invalid_frame_is_rejected(self):
        frame = demonstration_frame(1, 0.0, 0.0, 0.0)
        frame["position"]["latitude_deg"] = 91.0
        with self.assertRaises(FrameValidationError):
            validate_frame(frame)


class StoreTests(unittest.TestCase):
    def test_counts_drops_out_of_order_and_records_source_frames(self):
        with tempfile.TemporaryDirectory() as directory:
            recording = Path(directory) / "flight.ndjson"
            store = TelemetryStore("live", stale_ms=1000, record_path=recording)
            first = demonstration_frame(4, 1.0, 0.0, 0.0)
            first["attitude"]["quaternion"] = {"w": 2.0, "x": 0.0, "y": 0.0, "z": 0.0}
            store.publish(first)
            store.publish(demonstration_frame(7, 2.0, 0.0, 0.0))
            _, accepted = store.publish(demonstration_frame(6, 3.0, 0.0, 0.0))
            snapshot = store.snapshot()
            self.assertFalse(accepted)
            self.assertEqual(snapshot["received_count"], 3)
            self.assertEqual(snapshot["dropped_frames"], 2)
            self.assertEqual(snapshot["out_of_order_frames"], 1)
            self.assertEqual(snapshot["latest"]["sequence"], 7)
            store.close()
            records = [json.loads(line) for line in recording.read_text().splitlines()]
            self.assertEqual([item["frame"]["sequence"] for item in records], [4, 7, 6])
            self.assertEqual(records[0]["frame"]["attitude"]["quaternion"]["w"], 2.0)
            self.assertTrue(all("ground_receive_timestamp" in item for item in records))


class ServerTests(unittest.TestCase):
    def setUp(self):
        self.store = TelemetryStore("live", stale_ms=1000)
        try:
            self.server = GroundStationServer(("127.0.0.1", 0), self.store)
        except PermissionError:
            self.store.close()
            self.skipTest("local sockets are disabled by the execution sandbox")
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.store.close()
        self.thread.join(timeout=2)

    def request_json(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        request = Request(self.base + path, data=data, headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=2) as response:
            return response.status, json.load(response)

    def test_static_health_ingest_and_snapshot(self):
        with urlopen(self.base + "/", timeout=2) as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"Andromeda Flight View", response.read())
        status, initial = self.request_json("/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(initial["stale"])
        status, posted = self.request_json("/api/telemetry", demonstration_frame(10, 6.0, 0.0, 0.0))
        self.assertEqual(status, 202)
        self.assertTrue(posted["accepted_for_display"])
        _, snapshot = self.request_json("/api/state")
        self.assertEqual(snapshot["latest"]["sequence"], 10)
        self.assertFalse(snapshot["stale"])

    def test_invalid_ingest_returns_bad_request(self):
        frame = demonstration_frame(1, 0.0, 0.0, 0.0)
        frame["schema_version"] = 99
        with self.assertRaises(HTTPError) as caught:
            self.request_json("/api/telemetry", frame)
        self.assertEqual(caught.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
