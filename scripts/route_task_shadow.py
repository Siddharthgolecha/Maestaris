#!/usr/bin/env python3
"""Emit a zero-key advisory route for one task fixture.

This script intentionally performs no network or GitHub mutation.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from maestaris_orchestration.execution_routing import (
    System1Signal,
    TaskFeatures,
    apply_system1_signal,
    bounded_tool_plan,
    deterministic_route,
    executor_envelope,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="JSON task feature fixture")
    parser.add_argument("--output", help="optional JSON output path")
    args = parser.parse_args()

    policy = yaml.safe_load((ROOT / "tools/orchestrator/policy.yaml").read_text())
    data = json.loads(Path(args.input).read_text())
    features = TaskFeatures.from_mapping(data["features"])

    routing = policy["routing"]
    plan = deterministic_route(
        features,
        long_context_chars=int(routing["long_context_chars"]),
    )

    if data.get("system1_answers"):
        signal = System1Signal.from_typed_answers(
            data["system1_answers"],
            source=str(data.get("system1_source", "shadow-system1")),
        )
        plan = apply_system1_signal(
            plan,
            signal,
            upgrade_confidence=float(routing["upgrade_confidence"]),
            downgrade_confidence=float(routing["downgrade_confidence"]),
        )

    tool_policy = policy["tool_selection"]
    tool_plan = None
    if data.get("needle3_response"):
        tool_plan = bounded_tool_plan(
            data["needle3_response"],
            allowlisted_tools=tool_policy["allowlist"],
            minimum_confidence=float(tool_policy["minimum_confidence"]),
        )

    envelope = executor_envelope(
        repository=str(data.get("repository", "Siddharthgolecha/Maestaris")),
        issue_number=int(data.get("issue_number", 0)),
        branch=str(data.get("branch", "")),
        pr_number=data.get("pr_number"),
        expected_head_sha=data.get("expected_head_sha"),
        plan=plan,
        allowed_tools=tool_policy["allowlist"],
    )
    result = {
        "mode": "shadow",
        "route": plan.as_dict(),
        "tool_plan": tool_plan.as_dict() if tool_plan else None,
        "executor_envelope": envelope,
    }
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered)
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
