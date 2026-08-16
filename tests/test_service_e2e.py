import tempfile
import unittest

from andromeda_control.controller import ControllerService
from andromeda_control.scheduler import Scheduler
from andromeda_control.store import StateStore


class ServiceEndToEndTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.service = ControllerService(StateStore(self.tempdir.name), Scheduler(60, 120, 1))

    def tearDown(self):
        self.tempdir.cleanup()

    def test_register_submit_claim_complete(self):
        self.service.register_worker({
            "id": "worker3", "capabilities": {"python": "3.12", "rocketpy": "test"}, "resources": []
        })
        task = self.service.submit_task({
            "id": "TASK-E2E", "name": "e2e", "command": ["python3", "-V"],
            "required_capabilities": ["rocketpy"]
        })
        self.assertEqual(task["state"], "DISPATCHED")
        claimed = self.service.claim("worker3")
        self.assertEqual(claimed["state"], "RUNNING")
        finished = self.service.finish("worker3", "TASK-E2E", {
            "result": {"exit_code": 0, "stdout": "ok", "stderr": ""}, "artifacts": []
        }, succeeded=True)
        self.assertEqual(finished["state"], "SUCCEEDED")
        fetched = self.service.get_task("TASK-E2E")
        self.assertEqual(fetched["result"]["exit_code"], 0)
        self.assertGreaterEqual(len(fetched["history"]), 6)

    def test_worker_process_restart_requeues_running_task(self):
        self.service.register_worker({
            "id": "worker3", "session_id": "old", "capabilities": {"python": "3.12"}, "resources": []
        })
        self.service.submit_task({
            "id": "TASK-RESTART", "name": "restart", "command": ["python3", "-V"],
            "required_capabilities": ["python"]
        })
        self.service.claim("worker3")
        self.service.register_worker({
            "id": "worker3", "session_id": "new", "capabilities": {"python": "3.12"}, "resources": []
        })
        task = self.service.get_task("TASK-RESTART")
        self.assertEqual(task["state"], "RETRY_WAIT")
        self.assertEqual(task["infrastructure_retries"], 1)
        self.assertIsNone(task["assigned_worker"])


if __name__ == "__main__":
    unittest.main()
