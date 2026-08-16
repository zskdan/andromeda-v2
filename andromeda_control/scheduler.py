"""Capability/resource scheduler and heartbeat/retry reconciliation."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .models import TaskState, WorkerState, parse_time, transition, utc_now


class Scheduler:
    def __init__(self, suspect_after: int = 60, offline_after: int = 120, retry_delay: int = 5):
        if suspect_after <= 0 or offline_after <= suspect_after:
            raise ValueError("offline_after must be greater than suspect_after > 0")
        self.suspect_after = suspect_after
        self.offline_after = offline_after
        self.retry_delay = retry_delay

    def refresh_worker_states(self, state: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc)
        for worker in state["workers"].values():
            age = (now - parse_time(worker["last_seen"])).total_seconds()
            worker["state"] = (
                WorkerState.OFFLINE if age >= self.offline_after
                else WorkerState.SUSPECT if age >= self.suspect_after
                else WorkerState.ONLINE
            )

    @staticmethod
    def _available_resources(worker: dict[str, Any]) -> set[str]:
        return {
            str(resource["type"])
            for resource in worker.get("resources", [])
            if resource.get("state", "AVAILABLE") == "AVAILABLE"
        }

    def compatible(self, task: dict[str, Any], worker: dict[str, Any]) -> bool:
        if worker.get("state") != WorkerState.ONLINE:
            return False
        if len(worker.get("running_tasks", [])) >= int(worker.get("max_concurrent_tasks", 1)):
            return False
        capabilities = set(worker.get("capabilities", {}))
        if not set(task.get("required_capabilities", [])).issubset(capabilities):
            return False
        return set(task.get("required_resource_types", [])).issubset(self._available_resources(worker))

    def choose_worker(self, task: dict[str, Any], workers: dict[str, Any]) -> dict[str, Any] | None:
        candidates = [worker for worker in workers.values() if self.compatible(task, worker)]
        preferred = set(task.get("preferred_capabilities", []))
        candidates.sort(key=lambda worker: (
            -len(preferred.intersection(worker.get("capabilities", {}))),
            len(worker.get("running_tasks", [])),
            worker["id"],
        ))
        return candidates[0] if candidates else None

    def reconcile(self, state: dict[str, Any]) -> None:
        self.refresh_worker_states(state)
        now = datetime.now(timezone.utc)

        for task in state["tasks"].values():
            task_state = TaskState(task["state"])
            if task_state in {TaskState.DISPATCHED, TaskState.RUNNING}:
                worker = state["workers"].get(task.get("assigned_worker"))
                if not worker or worker.get("state") == WorkerState.OFFLINE:
                    self._infrastructure_failure(task, worker, "assigned worker went offline")

            if TaskState(task["state"]) is TaskState.RETRY_WAIT:
                retry_after = task.get("retry_after")
                if retry_after and parse_time(retry_after) <= now:
                    transition(task, TaskState.QUEUED, "retry delay elapsed")
                    task["retry_after"] = None

        pending = [
            task for task in state["tasks"].values()
            if TaskState(task["state"]) in {TaskState.QUEUED, TaskState.WAITING_FOR_RESOURCE}
        ]
        pending.sort(key=lambda task: (-int(task.get("priority", 50)), task["created_at"], task["id"]))
        for task in pending:
            worker = self.choose_worker(task, state["workers"])
            if worker:
                if TaskState(task["state"]) is TaskState.WAITING_FOR_RESOURCE:
                    transition(task, TaskState.READY, f"compatible worker {worker['id']} became available")
                else:
                    transition(task, TaskState.READY, f"matched worker {worker['id']}")
                task["assigned_worker"] = worker["id"]
                transition(task, TaskState.DISPATCHED, f"dispatched to {worker['id']}")
                worker.setdefault("running_tasks", []).append(task["id"])
            elif TaskState(task["state"]) is TaskState.QUEUED:
                transition(task, TaskState.WAITING_FOR_RESOURCE, "no compatible online worker")

    def _infrastructure_failure(
        self, task: dict[str, Any], worker: dict[str, Any] | None, reason: str
    ) -> None:
        if worker and task["id"] in worker.get("running_tasks", []):
            worker["running_tasks"].remove(task["id"])
        task["assigned_worker"] = None
        task["infrastructure_retries"] = int(task.get("infrastructure_retries", 0)) + 1
        if task["infrastructure_retries"] <= int(task.get("max_infrastructure_retries", 3)):
            transition(task, TaskState.RETRY_WAIT, reason)
            retry_at = datetime.now(timezone.utc).timestamp() + self.retry_delay
            task["retry_after"] = datetime.fromtimestamp(retry_at, timezone.utc).isoformat().replace("+00:00", "Z")
        else:
            task["failure"] = {"kind": "infrastructure", "message": reason, "at": utc_now()}
            transition(task, TaskState.FAILED, "infrastructure retry limit exhausted")
