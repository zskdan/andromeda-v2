#!/usr/bin/env python3
"""Enforce repository cross-domain change-impact evidence rules."""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RULES = ROOT / "integration" / "change-impact-rules.json"


def run_git(arguments):
    completed = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def working_tree_paths():
    output = run_git(["status", "--porcelain=v1", "--untracked-files=all"])
    paths = []
    for line in output.splitlines():
        if len(line) < 4:
            continue
        path = line[3:]
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path)
    return sorted(set(paths))


def committed_paths(base, head):
    output = run_git(["diff", "--name-only", "--diff-filter=ACMR", base, head])
    return sorted({line.strip() for line in output.splitlines() if line.strip()})


def matches(path, patterns):
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def assess(paths, rules_path):
    rules_document = json.loads(rules_path.read_text(encoding="utf-8"))
    try:
        portable_rules_path = rules_path.relative_to(ROOT).as_posix()
    except ValueError:
        portable_rules_path = rules_path.as_posix()
    assessments = []
    for rule in rules_document["rules"]:
        triggers = [path for path in paths if matches(path, rule["trigger_paths"])]
        if not triggers:
            continue
        evidence = [
            path for path in paths if matches(path, rule["acceptable_evidence_paths"])
        ]
        assessments.append(
            {
                "id": rule["id"],
                "status": "pass" if evidence else "fail",
                "trigger_paths": triggers,
                "evidence_paths": evidence,
                "review_owner": rule["review_owner"],
                "no_update_rule": rule["no_update_rule"],
            }
        )
    return {
        "schema_version": 1,
        "rules_path": portable_rules_path,
        "changed_paths": paths,
        "triggered_rule_count": len(assessments),
        "overall_status": "pass"
        if all(item["status"] == "pass" for item in assessments)
        else "fail",
        "assessments": assessments,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rules", type=Path, default=DEFAULT_RULES)
    parser.add_argument("--base", default="HEAD~1")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--working-tree", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    paths = working_tree_paths() if args.working_tree else committed_paths(args.base, args.head)
    result = assess(paths, args.rules.resolve())
    encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0 if result["overall_status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
