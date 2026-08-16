"""Outbound-polling Andromeda worker with an executable allowlist."""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import time
from typing import Any
from urllib.error import URLError
from uuid import uuid4

from .client import ApiError, request

LOG = logging.getLogger("andromeda.worker")


def load_config(path: str) -> dict[str, Any]:
    with open(path, encoding="utf-8") as handle:
        config = json.load(handle)
    required = {"id", "capabilities", "allowed_executables"}
    missing = required.difference(config)
    if missing:
        raise ValueError(f"worker config is missing: {', '.join(sorted(missing))}")
    if not isinstance(config["allowed_executables"], list):
        raise ValueError("allowed_executables must be a list")
    return config


def executable_allowed(command: list[str], allowlist: list[str]) -> bool:
    return command[0] in allowlist


def run_task(task: dict[str, Any], config: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    command = task["command"]
    if not executable_allowed(command, config["allowed_executables"]):
        return False, {
            "kind": "policy",
            "message": f"executable is not allowed on this worker: {command[0]}",
        }
    timeout = max(1, int(config.get("task_timeout_seconds", 3600)))
    work_dir = config.get("work_dir")
    try:
        completed = subprocess.run(
            command,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return False, {"kind": "command", "message": f"command timed out after {timeout}s", "stdout": exc.stdout, "stderr": exc.stderr}
    except OSError as exc:
        return False, {"kind": "infrastructure", "message": str(exc)}

    result = {
        "result": {
            "exit_code": completed.returncode,
            "stdout": completed.stdout[-100_000:],
            "stderr": completed.stderr[-100_000:],
        },
        "artifacts": [],
    }
    if completed.returncode == 0:
        return True, result
    return False, {
        "kind": "command",
        "message": f"command exited with status {completed.returncode}",
        **result["result"],
    }


class Worker:
    def __init__(self, controller: str, config: dict[str, Any], poll_interval: float = 5.0):
        self.controller = controller
        self.config = config
        self.worker_id = str(config["id"])
        self.session_id = uuid4().hex
        self.poll_interval = poll_interval

    def register(self) -> None:
        request(self.controller, "POST", "/v1/workers/register", {
            "id": self.worker_id,
            "session_id": self.session_id,
            "name": self.config.get("name", self.worker_id),
            "location": self.config.get("location", {"type": "unknown"}),
            "capabilities": self.config["capabilities"],
            "resources": self.config.get("resources", []),
            "max_concurrent_tasks": int(self.config.get("max_concurrent_tasks", 1)),
            "metadata": self.config.get("metadata", {}),
        })
        LOG.info("registered as %s", self.worker_id)

    def heartbeat(self) -> None:
        request(self.controller, "POST", f"/v1/workers/{self.worker_id}/heartbeat", {
            "capabilities": self.config["capabilities"],
            "resources": self.config.get("resources", []),
        })

    def poll_once(self) -> bool:
        self.heartbeat()
        task = request(self.controller, "POST", f"/v1/workers/{self.worker_id}/claim", {})
        if not task:
            return False
        LOG.info("running %s (%s)", task["id"], task["name"])
        succeeded, result = run_task(task, self.config)
        action = "complete" if succeeded else "fail"
        request(self.controller, "POST", f"/v1/workers/{self.worker_id}/tasks/{task['id']}/{action}", result)
        LOG.info("task %s %s", task["id"], "succeeded" if succeeded else "failed")
        return True

    def run(self, once: bool = False, stop_after_task: bool = False) -> None:
        registered = False
        while True:
            try:
                if not registered:
                    self.register()
                    registered = True
                ran_task = self.poll_once()
                if once or (stop_after_task and ran_task):
                    return
                time.sleep(self.poll_interval)
            except (URLError, ApiError, ConnectionError) as exc:
                registered = False
                LOG.warning("controller unavailable: %s", exc)
                if once:
                    raise
                time.sleep(self.poll_interval)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run an Andromeda v0.2 worker")
    parser.add_argument("--controller", default="http://127.0.0.1:8765")
    parser.add_argument("--config", required=True, help="path to a worker JSON configuration")
    parser.add_argument("--poll-interval", type=float, default=30.0)
    parser.add_argument("--once", action="store_true", help="register, poll once, then exit")
    parser.add_argument("--stop-after-task", action="store_true", help="exit after completing one task")
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper()), format="%(asctime)s %(levelname)s %(message)s")
    Worker(args.controller, load_config(args.config), args.poll_interval).run(args.once, args.stop_after_task)


if __name__ == "__main__":
    main()
