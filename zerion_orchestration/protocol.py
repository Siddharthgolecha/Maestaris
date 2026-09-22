from __future__ import annotations

import re
from typing import Iterable

TASK_TITLE_PREFIX = "[Zerion task]"
WORKER_TERMINAL = {"DONE", "BLOCKED", "NEEDS_REVIEW"}
REVIEW_STATES = {"ACCEPTED", "REVISE", "REJECTED"}
LEGACY_TASK_STATUSES = {"ASSIGNED"}
OPTIONAL_TASK_STATUSES = {"READY"} | LEGACY_TASK_STATUSES

_FIELD_RE = re.compile(r"^([a-z][a-z0-9_]*):\s*(.*)$", re.MULTILINE)
_WORKER_HEADER_RE = re.compile(r"^\[WORKER:([^:\]]+):v1\]")


def protocol_fields(body: str) -> dict[str, str]:
    return {
        match.group(1): match.group(2).strip()
        for match in _FIELD_RE.finditer(body or "")
    }


def worker_from_event(body: str) -> str | None:
    match = _WORKER_HEADER_RE.match((body or "").strip())
    if not match:
        return None
    worker = match.group(1).strip()
    return worker or None


def pinned_worker(issue_body: str) -> str | None:
    """Return an optional worker restriction from a task Issue body.

    Worker identity is normally established by the ACK event. A task body may
    include `worker:` only when the orchestrator intentionally pins the task to
    a specialist.
    """
    value = protocol_fields(issue_body).get("worker", "").strip()
    if not value or value.lower() == "unassigned":
        return None
    return value


def validate_task_issue(
    title: str,
    body: str,
    title_prefix: str = TASK_TITLE_PREFIX,
) -> list[str]:
    errors: list[str] = []
    body = body or ""

    if not title.startswith(title_prefix):
        return errors

    if not body.lstrip().startswith("[ORCHESTRATOR:v1]"):
        errors.append("task Issue body must start with [ORCHESTRATOR:v1]")

    fields = protocol_fields(body)

    # Queue semantics: the Issue itself is READY. Worker ownership begins only
    # with an ACK comment. Therefore worker/status are optional in new tasks.
    for key in ("task_id", "project", "priority"):
        if not fields.get(key):
            errors.append(f"task Issue is missing {key}")

    status = fields.get("status")
    if status and status not in OPTIONAL_TASK_STATUSES:
        errors.append(
            "task Issue status, when present, must be READY "
            "(legacy ASSIGNED is accepted during migration)"
        )

    worker = fields.get("worker")
    if worker is not None and not worker.strip():
        errors.append("task Issue worker must be omitted or non-empty")

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
        if not worker_from_event(body):
            errors.append("worker event header must identify a worker")
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


def reduce_task_status(comments: Iterable[str]) -> str:
    """Reduce Issue event history to a derived live status.

    An open Zerion task starts READY. The ACK, not the Issue body, establishes
    worker ownership.
    """
    status = "ready"

    for raw in comments:
        body = (raw or "").strip()
        fields = protocol_fields(body)

        if body.startswith("[WORKER:"):
            event = fields.get("status")
            if event == "ACK":
                status = "claimed"
            elif event == "BLOCKED":
                status = "blocked"
            elif event in {"DONE", "NEEDS_REVIEW"}:
                status = "needs_review"

        elif body.startswith("[ORCHESTRATOR-REVIEW:v1]"):
            event = fields.get("status")
            if event == "ACCEPTED":
                status = "accepted"
            elif event == "REVISE":
                status = "revise"
            elif event == "REJECTED":
                status = "rejected"

    return status


def desired_managed_labels(
    issue_body: str,
    comments: Iterable[str],
    github_config: dict,
) -> set[str]:
    fields = protocol_fields(issue_body)
    labels = {str(github_config["task_label"])}

    status = reduce_task_status(comments)
    status_labels = github_config["status_labels"]
    labels.add(str(status_labels[status]))

    priority = fields.get("priority")
    if priority:
        labels.add(f"{github_config['priority_label_prefix']}{priority}")

    return labels


def is_managed_label(label: str, github_config: dict) -> bool:
    if label == github_config.get("task_label"):
        return True
    if label in set((github_config.get("status_labels") or {}).values()):
        return True
    prefix = str(github_config.get("priority_label_prefix") or "")
    return bool(prefix and label.startswith(prefix))
