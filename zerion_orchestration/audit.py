from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from .protocol import desired_managed_labels, is_managed_label, protocol_fields, reduce_task_status


@dataclass(frozen=True)
class AuditFinding:
    code: str
    severity: str
    message: str
    repairable: bool = False


def audit_task(
    *,
    issue_body: str,
    comments: Iterable[str],
    labels: Iterable[str],
    github_config: dict,
    issue_open: bool = True,
    linked_pr_count: int = 0,
) -> list[AuditFinding]:
    """Audit one task without mutating canonical Issue history.

    Findings intentionally separate canonical contradictions from derived label drift.
    Callers may reconcile only findings marked repairable.
    """
    comments = tuple(comments)
    findings: list[AuditFinding] = []
    status = reduce_task_status(comments)
    fields = protocol_fields(issue_body)

    expected = desired_managed_labels(issue_body, comments, github_config)
    actual_managed = {label for label in labels if is_managed_label(label, github_config)}
    if actual_managed != expected:
        findings.append(AuditFinding(
            "derived-label-drift",
            "warning",
            f"managed labels differ: expected={sorted(expected)} actual={sorted(actual_managed)}",
            True,
        ))

    if status == "accepted" and issue_open:
        findings.append(AuditFinding(
            "accepted-open-mismatch", "warning", "accepted task Issue is still open", True
        ))

    if status == "needs_review":
        findings.append(AuditFinding(
            "unreviewed-terminal-result", "error", "terminal worker result awaits orchestrator review"
        ))

    if linked_pr_count and status == "ready":
        findings.append(AuditFinding(
            "orphan-pr", "warning", "linked PR exists but canonical Issue history has no ownership event"
        ))

    task_id = fields.get("task_id")
    if not task_id:
        findings.append(AuditFinding("missing-task-id", "error", "task Issue has no task_id"))
    return findings


def duplicate_task_ids(issue_bodies: Iterable[str]) -> set[str]:
    counts = Counter(
        task_id
        for body in issue_bodies
        if (task_id := protocol_fields(body).get("task_id"))
    )
    return {task_id for task_id, count in counts.items() if count > 1}


def reconcile_labels(
    issue_body: str,
    comments: Iterable[str],
    labels: Iterable[str],
    github_config: dict,
) -> set[str]:
    """Return the safe desired label set; never edits Issue comments/evidence."""
    unmanaged = {label for label in labels if not is_managed_label(label, github_config)}
    return unmanaged | desired_managed_labels(issue_body, comments, github_config)
