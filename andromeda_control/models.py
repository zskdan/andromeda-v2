"""Dependency-free domain models and validation helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4


class TaskState(StrEnum):
    SUBMITTED = "SUBMITTED"
    QUEUED = "QUEUED"
    WAITING_FOR_RESOURCE = "WAITING_FOR_RESOURCE"
    READY = "READY"
    DISPATCHED = "DISPATCHED"
    RUNNING = "RUNNING"
    RETRY_WAIT = "RETRY_WAIT"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class WorkerState(StrEnum):
    ONLINE = "ONLINE"
    SUSPECT = "SUSPECT"
    OFFLINE = "OFFLINE"


TERMINAL_TASK_STATES = {
    TaskState.SUCCEEDED,
    TaskState.FAILED,
    TaskState.CANCELLED,
}

ALLOWED_TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.SUBMITTED: {TaskState.QUEUED, TaskState.CANCELLED},
    TaskState.QUEUED: {TaskState.WAITING_FOR_RESOURCE, TaskState.READY, TaskState.CANCELLED},
    TaskState.WAITING_FOR_RESOURCE: {TaskState.READY, TaskState.CANCELLED},
    TaskState.READY: {TaskState.DISPATCHED, TaskState.WAITING_FOR_RESOURCE, TaskState.CANCELLED},
    TaskState.DISPATCHED: {TaskState.RUNNING, TaskState.RETRY_WAIT, TaskState.CANCELLED},
    TaskState.RUNNING: {TaskState.SUCCEEDED, TaskState.FAILED, TaskState.RETRY_WAIT, TaskState.CANCELLED},
    TaskState.RETRY_WAIT: {TaskState.QUEUED, TaskState.WAITING_FOR_RESOURCE, TaskState.CANCELLED},
    TaskState.SUCCEEDED: set(),
    TaskState.FAILED: set(),
    TaskState.CANCELLED: set(),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def new_id(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


def require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def string_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key, [])
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"{key} must be a list of non-empty strings")
    return sorted(set(value))


def normalize_worker(data: dict[str, Any]) -> dict[str, Any]:
    worker_id = require_string(data, "id")
    capabilities = data.get("capabilities", {})
    resources = data.get("resources", [])
    if not isinstance(capabilities, dict):
        raise ValueError("capabilities must be an object mapping names to versions")
    if not isinstance(resources, list):
        raise ValueError("resources must be a list")
    for resource in resources:
        if not isinstance(resource, dict) or not resource.get("id") or not resource.get("type"):
            raise ValueError("each resource requires id and type")
    now = utc_now()
    return {
        "id": worker_id,
        "name": str(data.get("name", worker_id)),
        "session_id": data.get("session_id"),
        "location": data.get("location", {"type": "unknown"}),
        "capabilities": {str(k): str(v) for k, v in capabilities.items()},
        "resources": resources,
        "max_concurrent_tasks": max(1, int(data.get("max_concurrent_tasks", 1))),
        "state": WorkerState.ONLINE,
        "registered_at": data.get("registered_at", now),
        "last_seen": now,
        "running_tasks": [],
        "metadata": data.get("metadata", {}),
    }


def normalize_task(data: dict[str, Any]) -> dict[str, Any]:
    name = require_string(data, "name")
    command = data.get("command")
    if not isinstance(command, list) or not command or any(not isinstance(part, str) for part in command):
        raise ValueError("command must be a non-empty array of strings")
    now = utc_now()
    retry = data.get("retry_policy", {})
    if not isinstance(retry, dict):
        raise ValueError("retry_policy must be an object")
    return {
        "id": str(data.get("id") or new_id("TASK")),
        "name": name,
        "owner": str(data.get("owner", "architect")),
        "command": command,
        "required_capabilities": string_list(data, "required_capabilities"),
        "preferred_capabilities": string_list(data, "preferred_capabilities"),
        "required_resource_types": string_list(data, "required_resource_types"),
        "priority": int(data.get("priority", 50)),
        "state": TaskState.SUBMITTED,
        "assigned_worker": None,
        "attempts": 0,
        "infrastructure_retries": 0,
        "max_infrastructure_retries": max(0, int(retry.get("max_infrastructure_retries", 3))),
        "retry_after": None,
        "created_at": now,
        "updated_at": now,
        "started_at": None,
        "finished_at": None,
        "result": None,
        "failure": None,
        "artifacts": [],
        "history": [{"at": now, "from": None, "to": TaskState.SUBMITTED, "reason": "submitted"}],
        "metadata": data.get("metadata", {}),
    }


def transition(task: dict[str, Any], target: TaskState, reason: str) -> None:
    current = TaskState(task["state"])
    if target not in ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"invalid task transition: {current} -> {target}")
    now = utc_now()
    task["state"] = target
    task["updated_at"] = now
    task.setdefault("history", []).append({"at": now, "from": current, "to": target, "reason": reason})
    if target is TaskState.RUNNING and not task.get("started_at"):
        task["started_at"] = now
    if target in TERMINAL_TASK_STATES:
        task["finished_at"] = now
