"""Minimal persistent Andromeda controller and HTTP API."""

from __future__ import annotations

import argparse
import json
import logging
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

from .models import TaskState, normalize_task, normalize_worker, transition, utc_now
from .scheduler import Scheduler
from .store import StateStore

LOG = logging.getLogger("andromeda.controller")


class ControllerService:
    def __init__(self, store: StateStore, scheduler: Scheduler):
        self.store = store
        self.scheduler = scheduler

    def health(self) -> dict[str, Any]:
        snapshot = self.store.snapshot()
        return {"status": "ok", "version": "0.2.0", "workers": len(snapshot["workers"]), "tasks": len(snapshot["tasks"])}

    def list_workers(self) -> list[dict[str, Any]]:
        with self.store.transaction() as state:
            self.scheduler.refresh_worker_states(state)
            return sorted(state["workers"].values(), key=lambda item: item["id"])

    def list_tasks(self) -> list[dict[str, Any]]:
        with self.store.transaction() as state:
            self.scheduler.reconcile(state)
            return sorted(state["tasks"].values(), key=lambda item: item["created_at"])

    def get_task(self, task_id: str) -> dict[str, Any]:
        snapshot = self.store.snapshot()
        try:
            return snapshot["tasks"][task_id]
        except KeyError as exc:
            raise KeyError(f"unknown task: {task_id}") from exc

    def register_worker(self, payload: dict[str, Any]) -> dict[str, Any]:
        worker = normalize_worker(payload)
        with self.store.transaction() as state:
            self.scheduler.reconcile(state)
            existing = state["workers"].get(worker["id"])
            if existing:
                old_session = existing.get("session_id")
                new_session = worker.get("session_id")
                if old_session and new_session and old_session != new_session:
                    for task in state["tasks"].values():
                        if task.get("assigned_worker") == worker["id"] and task["state"] in {TaskState.DISPATCHED, TaskState.RUNNING}:
                            self.scheduler._infrastructure_failure(task, existing, "worker process restarted")
                worker["registered_at"] = existing["registered_at"]
                worker["running_tasks"] = existing.get("running_tasks", [])
            state["workers"][worker["id"]] = worker
            self.scheduler.reconcile(state)
        LOG.info("worker %s registered", worker["id"])
        return worker

    def heartbeat(self, worker_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self.store.transaction() as state:
            self.scheduler.reconcile(state)
            if worker_id not in state["workers"]:
                raise KeyError(f"unknown worker: {worker_id}; register first")
            worker = state["workers"][worker_id]
            worker["last_seen"] = utc_now()
            worker["state"] = "ONLINE"
            for field in ("capabilities", "resources", "metadata"):
                if field in payload:
                    worker[field] = payload[field]
            self.scheduler.reconcile(state)
            return worker

    def submit_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        task = normalize_task(payload)
        with self.store.transaction() as state:
            if task["id"] in state["tasks"]:
                raise ValueError(f"task id already exists: {task['id']}")
            state["tasks"][task["id"]] = task
            transition(task, TaskState.QUEUED, "accepted by controller")
            self.scheduler.reconcile(state)
        LOG.info("task %s submitted", task["id"])
        return task

    def claim(self, worker_id: str) -> dict[str, Any] | None:
        with self.store.transaction() as state:
            if worker_id not in state["workers"]:
                raise KeyError(f"unknown worker: {worker_id}")
            worker = state["workers"][worker_id]
            worker["last_seen"] = utc_now()
            self.scheduler.reconcile(state)
            tasks = [
                task for task in state["tasks"].values()
                if task.get("assigned_worker") == worker_id and task["state"] == TaskState.DISPATCHED
            ]
            tasks.sort(key=lambda task: (-int(task["priority"]), task["created_at"]))
            if not tasks:
                return None
            task = tasks[0]
            task["attempts"] = int(task.get("attempts", 0)) + 1
            transition(task, TaskState.RUNNING, f"claimed by {worker_id}")
            return task

    def finish(self, worker_id: str, task_id: str, payload: dict[str, Any], succeeded: bool) -> dict[str, Any]:
        with self.store.transaction() as state:
            task = state["tasks"].get(task_id)
            if not task:
                raise KeyError(f"unknown task: {task_id}")
            if task.get("assigned_worker") != worker_id:
                raise ValueError(f"task {task_id} is not assigned to {worker_id}")
            if task["state"] != TaskState.RUNNING:
                raise ValueError(f"task {task_id} is not RUNNING")
            worker = state["workers"].get(worker_id)
            if worker and task_id in worker.get("running_tasks", []):
                worker["running_tasks"].remove(task_id)
            if succeeded:
                task["result"] = payload.get("result", payload)
                task["artifacts"] = payload.get("artifacts", [])
                transition(task, TaskState.SUCCEEDED, f"completed by {worker_id}")
            elif payload.get("kind") == "infrastructure":
                self.scheduler._infrastructure_failure(task, worker, str(payload.get("message", "worker infrastructure failure")))
            else:
                task["failure"] = {"kind": payload.get("kind", "command"), "message": payload.get("message", "task failed"), "at": utc_now()}
                transition(task, TaskState.FAILED, f"execution failed on {worker_id}")
            self.scheduler.reconcile(state)
            return task

    def cancel(self, task_id: str) -> dict[str, Any]:
        with self.store.transaction() as state:
            task = state["tasks"].get(task_id)
            if not task:
                raise KeyError(f"unknown task: {task_id}")
            if task["state"] in {TaskState.SUCCEEDED, TaskState.FAILED, TaskState.CANCELLED}:
                raise ValueError("terminal tasks cannot be cancelled")
            worker = state["workers"].get(task.get("assigned_worker"))
            if worker and task_id in worker.get("running_tasks", []):
                worker["running_tasks"].remove(task_id)
            transition(task, TaskState.CANCELLED, "cancelled through API")
            return task


class ApiHandler(BaseHTTPRequestHandler):
    server: "ControllerServer"

    def log_message(self, fmt: str, *args: Any) -> None:
        LOG.info("%s - %s", self.address_string(), fmt % args)

    def _json(self, status: int, body: Any) -> None:
        encoded = json.dumps(body, indent=2).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _payload(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 1_000_000:
            raise ValueError("request body is too large")
        raw = self.rfile.read(length)
        value = json.loads(raw or b"{}")
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object")
        return value

    def _dispatch(self) -> tuple[int, Any]:
        path = urlparse(self.path).path.rstrip("/") or "/"
        parts = path.strip("/").split("/")
        service = self.server.service
        if self.command == "GET" and path == "/health":
            return HTTPStatus.OK, service.health()
        if self.command == "GET" and path == "/v1/workers":
            return HTTPStatus.OK, {"workers": service.list_workers()}
        if self.command == "GET" and path == "/v1/tasks":
            return HTTPStatus.OK, {"tasks": service.list_tasks()}
        if self.command == "GET" and len(parts) == 3 and parts[:2] == ["v1", "tasks"]:
            return HTTPStatus.OK, service.get_task(parts[2])
        if self.command == "POST" and path == "/v1/workers/register":
            return HTTPStatus.CREATED, service.register_worker(self._payload())
        if self.command == "POST" and len(parts) == 4 and parts[:2] == ["v1", "workers"] and parts[3] == "heartbeat":
            return HTTPStatus.OK, service.heartbeat(parts[2], self._payload())
        if self.command == "POST" and len(parts) == 4 and parts[:2] == ["v1", "workers"] and parts[3] == "claim":
            task = service.claim(parts[2])
            return (HTTPStatus.OK, task) if task else (HTTPStatus.NO_CONTENT, None)
        if self.command == "POST" and path == "/v1/tasks":
            return HTTPStatus.CREATED, service.submit_task(self._payload())
        if self.command == "POST" and len(parts) == 4 and parts[:2] == ["v1", "tasks"] and parts[3] == "cancel":
            return HTTPStatus.OK, service.cancel(parts[2])
        if self.command == "POST" and len(parts) == 6 and parts[:2] == ["v1", "workers"] and parts[3] == "tasks":
            if parts[5] == "complete":
                return HTTPStatus.OK, service.finish(parts[2], parts[4], self._payload(), True)
            if parts[5] == "fail":
                return HTTPStatus.OK, service.finish(parts[2], parts[4], self._payload(), False)
        return HTTPStatus.NOT_FOUND, {"error": "not found"}

    def _handle(self) -> None:
        try:
            status, body = self._dispatch()
            self._json(status, body)
        except KeyError as exc:
            self._json(HTTPStatus.NOT_FOUND, {"error": str(exc)})
        except (ValueError, json.JSONDecodeError) as exc:
            self._json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception:
            LOG.exception("unhandled API error")
            self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "internal server error"})

    do_GET = _handle
    do_POST = _handle


class ControllerServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], service: ControllerService):
        self.service = service
        super().__init__(address, ApiHandler)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Andromeda v0.2 controller")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--state-dir", default=".andromeda-state")
    parser.add_argument("--suspect-after", type=int, default=60)
    parser.add_argument("--offline-after", type=int, default=120)
    parser.add_argument("--retry-delay", type=int, default=5)
    parser.add_argument("--log-level", default="INFO")
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    logging.basicConfig(level=getattr(logging, args.log_level.upper()), format="%(asctime)s %(levelname)s %(message)s")
    scheduler = Scheduler(args.suspect_after, args.offline_after, args.retry_delay)
    server = ControllerServer((args.host, args.port), ControllerService(StateStore(args.state_dir), scheduler))
    LOG.info("controller listening on http://%s:%s", args.host, args.port)
    try:
        server.serve_forever(poll_interval=0.5)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
