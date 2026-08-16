import unittest

from andromeda_control.models import TaskState, normalize_task, transition


class ModelTests(unittest.TestCase):
    def test_task_normalization_and_lifecycle(self):
        task = normalize_task({"name": "demo", "command": ["python3", "-V"]})
        self.assertEqual(task["state"], TaskState.SUBMITTED)
        transition(task, TaskState.QUEUED, "test")
        transition(task, TaskState.WAITING_FOR_RESOURCE, "test")
        transition(task, TaskState.CANCELLED, "test")
        self.assertEqual(task["state"], TaskState.CANCELLED)
        self.assertEqual(len(task["history"]), 4)

    def test_invalid_transition_is_rejected(self):
        task = normalize_task({"name": "demo", "command": ["python3", "-V"]})
        with self.assertRaises(ValueError):
            transition(task, TaskState.RUNNING, "skip states")

    def test_command_must_be_argument_array(self):
        with self.assertRaises(ValueError):
            normalize_task({"name": "unsafe", "command": "echo hello"})


if __name__ == "__main__":
    unittest.main()
