"""Submission and status command-line clients."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from .client import request


def _load_json(path: str) -> dict[str, Any]:
    if path == "-":
        return json.load(sys.stdin)
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def submit_main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Submit a task to Andromeda")
    parser.add_argument("task_file", help="JSON task file, or - for stdin")
    parser.add_argument("--controller", default="http://127.0.0.1:8765")
    args = parser.parse_args(argv)
    print(json.dumps(request(args.controller, "POST", "/v1/tasks", _load_json(args.task_file)), indent=2))


def status_main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Show Andromeda workers and tasks")
    parser.add_argument("--controller", default="http://127.0.0.1:8765")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    workers = request(args.controller, "GET", "/v1/workers")["workers"]
    tasks = request(args.controller, "GET", "/v1/tasks")["tasks"]
    if args.json:
        print(json.dumps({"workers": workers, "tasks": tasks}, indent=2))
        return
    print("WORKERS")
    for worker in workers:
        capabilities = ", ".join(worker["capabilities"]) or "-"
        print(f"  {worker['id']:<16} {worker['state']:<8} {capabilities}")
    print("TASKS")
    for task in tasks:
        print(f"  {task['id']:<20} {task['state']:<22} {task['name']}")
