from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math
import re
from typing import Iterable

TASK_TITLE_PREFIX = "[Maestaris task]"
WORKER_TERMINAL = {"DONE", "BLOCKED", "NEEDS_REVIEW"}
REVIEW_STATES = {"ACCEPTED", "REVISE", "REJECTED"}
LEGACY_TASK_STATUSES = {"ASSIGNED"}
OPTIONAL_TASK_STATUSES = {"READY"} | LEGACY_TASK_STATUSES

_FIELD_RE = re.compile(r"^([a-z][a-z0-9_]*):\s*(.*)$", re.MULTILINE)
_WORKER_HEADER_RE = re.compile(r"^\[WORKER:([^:\]]+):v1\]")


def protocol_fields(body: str) -> dict[str, str]:
    return {match.group(1): match.group(2).strip() for match in _FIELD_RE.finditer(body or "")}


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


def validate_task_issue(title: str, body: str, title_prefix: str = TASK_TITLE_PREFIX) -> list[str]:
    errors: list[str] = []
    body = body or ""
    if not title.startswith(title_prefix):
        return errors
    if not body.lstrip().startswith("[ORCHESTRATOR:v1]"):
        errors.append("task Issue body must start with [ORCHESTRATOR:v1]")
    fields = protocol_fields(body)
    for key in ("task_id", "project", "priority"):
        if not fields.get(key):
            errors.append(f"task Issue is missing {key}")
    status = fields.get("status")
    if status and status not in OPTIONAL_TASK_STATUSES:
        errors.append("task Issue status, when present, must be READY (legacy ASSIGNED is accepted during migration)")
    worker = fields.get("worker")
    if worker is not None and not worker.strip():
        errors.append("task Issue worker must be omitted or non-empty")
    if not fields.get("objective") and "## Objective" not in body:
        errors.append("task Issue must define objective or a ## Objective section")
    return errors


def _parse_time(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _parse_positive_finite_hours(value: str) -> float | None:
    try:
        hours = float(value)
        if not math.isfinite(hours) or hours <= 0:
            return None
        return hours
    except (TypeError, ValueError):
        return None


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
        if status in {"ACK", "RENEW"}:
            for key in ("dispatcher", "claimed_at", "lease_hours"):
                if not fields.get(key):
                    errors.append(f"{status} is missing {key}")
            # ACK predates strict lease parsing and existing v0.6 histories may use
            # symbolic timestamps such as `now`. Preserve that compatibility while
            # making the new first-class RENEW event mechanically well-formed.
            if status == "RENEW" and fields.get("claimed_at") and _parse_time(fields["claimed_at"]) is None:
                errors.append("RENEW claimed_at must be an ISO timestamp")
            if status == "RENEW" and fields.get("lease_hours") and _parse_positive_finite_hours(fields["lease_hours"]) is None:
                errors.append("RENEW lease_hours must be a positive finite number")
        elif status in WORKER_TERMINAL:
            if "summary" not in fields and "## Summary" not in body:
                errors.append(f"{status} event must include summary")
        else:
            errors.append("worker status must be ACK, RENEW, DONE, BLOCKED, or NEEDS_REVIEW")
        return errors
    if body.startswith("[ORCHESTRATOR-CLAIM:v1]"):
        errors = []
        for key in ("task_id", "orchestrator", "claimed_at", "lease_hours"):
            if not fields.get(key):
                errors.append(f"orchestrator claim is missing {key}")
        if fields.get("claimed_at") and _parse_time(fields["claimed_at"]) is None:
            errors.append("orchestrator claim claimed_at must be an ISO timestamp")
        if fields.get("lease_hours") and _parse_positive_finite_hours(fields["lease_hours"]) is None:
            errors.append("orchestrator claim lease_hours must be a positive finite number")
        return errors
    if body.startswith("[ORCHESTRATOR-REVIEW:v1]"):
        errors = []
        if not fields.get("task_id"):
            errors.append("orchestrator review is missing task_id")
        status = fields.get("status")
        if status not in REVIEW_STATES:
            errors.append("orchestrator review status must be ACCEPTED, REVISE, or REJECTED")
        return errors
    return []


def active_review_claim(comments: Iterable[str], now: datetime | None = None) -> dict[str, str] | None:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    active: dict[str, str] | None = None
    active_claimed_at: datetime | None = None
    active_expires_at: datetime | None = None
    for raw in comments:
        body = (raw or "").strip()
        if body.startswith("[ORCHESTRATOR-CLAIM:v1]"):
            fields = protocol_fields(body)
            if not all(fields.get(k) for k in ("task_id", "orchestrator", "claimed_at", "lease_hours")):
                continue
            claimed_at = _parse_time(fields["claimed_at"])
            hours = _parse_positive_finite_hours(fields["lease_hours"])
            if claimed_at is None or hours is None or claimed_at > now:
                continue
            try:
                expires_at = claimed_at + timedelta(hours=hours)
            except OverflowError:
                continue
            if active is not None and active_expires_at is not None:
                if fields["orchestrator"] == active.get("orchestrator"):
                    if active_claimed_at is not None and claimed_at >= active_claimed_at and expires_at > active_expires_at:
                        active, active_claimed_at, active_expires_at = fields, claimed_at, expires_at
                    continue
                if claimed_at < active_expires_at:
                    continue
            active, active_claimed_at, active_expires_at = fields, claimed_at, expires_at
        elif body.startswith("[ORCHESTRATOR-REVIEW:v1]"):
            active = active_claimed_at = active_expires_at = None
    if not active or active_expires_at is None or active_expires_at <= now:
        return None
    return active


def review_claim_available(comments: Iterable[str], orchestrator: str, now: datetime | None = None) -> bool:
    active = active_review_claim(comments, now=now)
    return active is None or active.get("orchestrator") == orchestrator


def reduce_task_status(comments: Iterable[str]) -> str:
    """Reduce Issue event history to a derived live status."""
    status = "ready"
    for raw in comments:
        body = (raw or "").strip()
        fields = protocol_fields(body)
        if body.startswith("[WORKER:"):
            event = fields.get("status")
            if event in {"ACK", "RENEW"}:
                status = "claimed"
            elif event == "BLOCKED":
                status = "blocked"
            elif event in {"DONE", "NEEDS_REVIEW"}:
                status = "needs_review"
        elif body.startswith("[ORCHESTRATOR-REVIEW:v1]"):
            event = fields.get("status")
            if event == "ACCEPTED": status = "accepted"
            elif event == "REVISE": status = "revise"
            elif event == "REJECTED": status = "rejected"
    return status


def desired_managed_labels(issue_body: str, comments: Iterable[str], github_config: dict) -> set[str]:
    fields = protocol_fields(issue_body)
    labels = {str(github_config["task_label"])}
    status = reduce_task_status(comments)
    labels.add(str(github_config["status_labels"][status]))
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
