from __future__ import annotations

import re

TASK_TITLE_PREFIX = "[Zerion task]"
WORKER_TERMINAL = {"DONE", "BLOCKED", "NEEDS_REVIEW"}
REVIEW_STATES = {"ACCEPTED", "REVISE", "REJECTED"}

_FIELD_RE = re.compile(r"^([a-z][a-z0-9_]*):\s*(.*)$", re.MULTILINE)


def protocol_fields(body: str) -> dict[str, str]:
    return {
        match.group(1): match.group(2).strip()
        for match in _FIELD_RE.finditer(body or "")
    }


def validate_task_issue(title: str, body: str) -> list[str]:
    errors: list[str] = []
    body = body or ""

    if not title.startswith(TASK_TITLE_PREFIX):
        return errors

    if not body.lstrip().startswith("[ORCHESTRATOR:v1]"):
        errors.append("task Issue body must start with [ORCHESTRATOR:v1]")

    fields = protocol_fields(body)
    for key in ("task_id", "project", "worker", "status", "priority"):
        if not fields.get(key):
            errors.append(f"task Issue is missing {key}")

    if fields.get("status") and fields["status"] != "ASSIGNED":
        errors.append("new task Issue status must be ASSIGNED")

    if not fields.get("objective") and "## Objective" not in body:
        errors.append("task Issue must define objective or a ## Objective section")

    return errors


def validate_protocol_comment(body: str) -> list[str]:
    body = (body or "").strip()
    if not body:
        return []

    fields = protocol_fields(body)

    if body.startswith("[WORKER:"):
        errors: list[str] = []
        if not fields.get("task_id"):
            errors.append("worker event is missing task_id")
        status = fields.get("status")
        if not status:
            errors.append("worker event is missing status")
            return errors

        if status == "ACK":
            for key in ("dispatcher", "claimed_at", "lease_hours"):
                if not fields.get(key):
                    errors.append(f"ACK is missing {key}")
        elif status in WORKER_TERMINAL:
            if "summary" not in fields and "## Summary" not in body:
                errors.append(f"{status} event must include summary")
        else:
            errors.append(
                "worker status must be ACK, DONE, BLOCKED, or NEEDS_REVIEW"
            )
        return errors

    if body.startswith("[ORCHESTRATOR-REVIEW:v1]"):
        errors = []
        if not fields.get("task_id"):
            errors.append("orchestrator review is missing task_id")
        status = fields.get("status")
        if status not in REVIEW_STATES:
            errors.append(
                "orchestrator review status must be ACCEPTED, REVISE, or REJECTED"
            )
        return errors

    return []
