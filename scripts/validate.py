#!/usr/bin/env python3
"""Validate release structure, structured files, imports, and tests."""

from __future__ import annotations

import compileall
import json
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = [
    "README.md", "AGENTS.md", "LICENSE", "pyproject.toml", ".codex/config.toml",
    "andromeda_control/controller.py", "andromeda_control/worker.py",
    "control/schemas/task.schema.json", "control/schemas/worker.schema.json",
    "control/schemas/resource.schema.json", "control/schemas/heartbeat.schema.json",
    "control/policies/scheduler.json", "control/policies/retry.json",
    "prompts/chatgpt-control-console.md", "tests/test_service_e2e.py",
    "integration/change-impact-rules.json", "scripts/check_change_impact.py",
]


def main() -> int:
    missing = [name for name in REQUIRED if not (ROOT / name).is_file()]
    if missing:
        print("Missing required files:", *missing, sep="\n  ")
        return 1

    for path in sorted(ROOT.rglob("*.json")):
        with path.open(encoding="utf-8") as handle:
            json.load(handle)

    impact_rules = json.loads(
        (ROOT / "integration/change-impact-rules.json").read_text(encoding="utf-8")
    )
    required_rule_fields = {
        "id",
        "statement",
        "trigger_owner",
        "review_owner",
        "trigger_paths",
        "acceptable_evidence_paths",
        "required_assessment",
        "no_update_rule",
    }
    rules = impact_rules.get("rules", [])
    if not rules:
        raise ValueError("change-impact rule set is empty")
    rule_ids = [rule.get("id") for rule in rules]
    if len(rule_ids) != len(set(rule_ids)):
        raise ValueError("duplicate change-impact rule ID")
    for rule in rules:
        missing_fields = required_rule_fields - set(rule)
        if missing_fields:
            raise ValueError(
                f"change-impact rule {rule.get('id', '<unknown>')} missing: "
                f"{sorted(missing_fields)}"
            )
    for path in sorted(ROOT.rglob("*.toml")):
        with path.open("rb") as handle:
            tomllib.load(handle)
    for path in sorted(ROOT.rglob("*.yaml")):
        text = path.read_text(encoding="utf-8")
        if not text.strip() or "\t" in text:
            raise ValueError(f"invalid YAML hygiene: {path}")

    if not compileall.compile_dir(ROOT / "andromeda_control", quiet=1):
        return 1
    completed = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        check=False,
    )
    if completed.returncode:
        return completed.returncode
    print(f"Validated Andromeda Agent Framework v0.2 ({len(list(ROOT.rglob('*')))} filesystem entries).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
