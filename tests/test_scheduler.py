import unittest

from andromeda_control.models import TaskState, normalize_task, normalize_worker, transition
from andromeda_control.scheduler import Scheduler


class SchedulerTests(unittest.TestCase):
    def setUp(self):
        self.scheduler = Scheduler(suspect_after=60, offline_after=120, retry_delay=1)

    def queued(self, payload):
        task = normalize_task(payload)
        transition(task, TaskState.QUEUED, "test")
        return task

    def test_waits_without_matching_worker(self):
        task = self.queued({"name": "Vivado", "command": ["vivado"], "required_capabilities": ["vivado"]})
        state = {"workers": {}, "tasks": {task["id"]: task}}
        self.scheduler.reconcile(state)
        self.assertEqual(task["state"], TaskState.WAITING_FOR_RESOURCE)

    def test_matches_capability_and_resource(self):
        worker = normalize_worker({
            "id": "worker2",
            "capabilities": {"jtag": "1"},
            "resources": [{"id": "board-1", "type": "zcu102", "state": "AVAILABLE"}],
        })
        task = self.queued({
            "name": "HIL",
            "command": ["python3", "test.py"],
            "required_capabilities": ["jtag"],
            "required_resource_types": ["zcu102"],
        })
        state = {"workers": {worker["id"]: worker}, "tasks": {task["id"]: task}}
        self.scheduler.reconcile(state)
        self.assertEqual(task["state"], TaskState.DISPATCHED)
        self.assertEqual(task["assigned_worker"], "worker2")

    def test_preferred_capability_breaks_tie(self):
        first = normalize_worker({"id": "a", "capabilities": {"python": "3.12"}})
        preferred = normalize_worker({"id": "z", "capabilities": {"python": "3.12", "rocketpy": "1"}})
        task = self.queued({
            "name": "simulation", "command": ["python3", "sim.py"],
            "required_capabilities": ["python"], "preferred_capabilities": ["rocketpy"],
        })
        chosen = self.scheduler.choose_worker(task, {"a": first, "z": preferred})
        self.assertEqual(chosen["id"], "z")


if __name__ == "__main__":
    unittest.main()
