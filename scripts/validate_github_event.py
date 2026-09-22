#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from zerion_orchestration.protocol import (
    TASK_TITLE_PREFIX,
    validate_protocol_comment,
    validate_task_issue,
)


def main() -> int:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("GITHUB_EVENT_PATH is not set; nothing to validate.")
        return 0

    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    issue = event.get("issue") or {}
    comment = event.get("comment") or {}

    errors: list[str] = []

    title = issue.get("title") or ""
    body = issue.get("body") or ""
    if title.startswith(TASK_TITLE_PREFIX):
        errors.extend(validate_task_issue(title, body))

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
