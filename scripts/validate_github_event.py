#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

import yaml

RUNTIME_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(os.environ.get("ZERION_PROJECT_ROOT", str(RUNTIME_ROOT))).resolve()
sys.path.insert(0, str(RUNTIME_ROOT))

from zerion_orchestration.protocol import (
    validate_protocol_comment,
    validate_task_issue,
)


def main() -> int:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("GITHUB_EVENT_PATH is not set; nothing to validate.")
        return 0

    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    registry = yaml.safe_load(
        (PROJECT_ROOT / "coordination" / "zerion.yaml").read_text()
    )
    github = registry["github"]

    issue = event.get("issue") or {}
    comment = event.get("comment") or {}
    title = issue.get("title") or ""
    body = issue.get("body") or ""

    errors: list[str] = []
    errors.extend(
        validate_task_issue(
            title,
            body,
            title_prefix=str(github["task_title_prefix"]),
        )
    )

    comment_body = comment.get("body") or ""
    if comment_body.startswith("[WORKER:") or comment_body.startswith(
        "[ORCHESTRATOR-REVIEW:v1]"
    ):
        errors.extend(validate_protocol_comment(comment_body))

    if errors:
        print("Zerion GitHub protocol validation FAILED")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Zerion GitHub protocol validation OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
