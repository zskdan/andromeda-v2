import unittest

from andromeda_control.worker import executable_allowed, run_task


class WorkerTests(unittest.TestCase):
    def test_allowlist_uses_executable_not_shell(self):
        self.assertTrue(executable_allowed(["python3", "-V"], ["python3"]))
        self.assertFalse(executable_allowed(["/tmp/python3", "-V"], ["python3"]))
        self.assertFalse(executable_allowed(["sh", "-c", "anything"], ["python3"]))

    def test_rejected_command_is_policy_failure(self):
        ok, result = run_task(
            {"command": ["sh", "-c", "echo no"]},
            {"allowed_executables": ["python3"], "task_timeout_seconds": 1},
        )
        self.assertFalse(ok)
        self.assertEqual(result["kind"], "policy")


if __name__ == "__main__":
    unittest.main()
