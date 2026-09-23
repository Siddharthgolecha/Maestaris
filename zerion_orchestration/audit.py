from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Iterable, Mapping

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
    known_task_ids: Iterable[str] = (),
) -> list[AuditFinding]:
    """Audit one task without mutating canonical Issue history."""
    comments = tuple(comments)
    findings: list[AuditFinding] = []
    status = reduce_task_status(comments)
    fields = protocol_fields(issue_body)

    expected = desired_managed_labels(issue_body, comments, github_config)
    actual_managed = {label for label in labels if is_managed_label(label, github_config)}
    if actual_managed != expected:
        findings.append(AuditFinding(
            "derived-label-drift", "warning",
            f"managed labels differ: expected={sorted(expected)} actual={sorted(actual_managed)}", True,
        ))

    if status == "accepted" and issue_open:
        findings.append(AuditFinding("accepted-open-mismatch", "warning", "accepted task Issue is still open", True))
    if status == "needs_review":
        findings.append(AuditFinding("unreviewed-terminal-result", "error", "terminal worker result awaits orchestrator review"))
    if linked_pr_count and status == "ready":
        findings.append(AuditFinding("orphan-pr", "warning", "linked PR exists but canonical Issue history has no ownership event"))

    task_id = fields.get("task_id")
    if not task_id:
        findings.append(AuditFinding("missing-task-id", "error", "task Issue has no task_id"))

    known = set(known_task_ids)
    for dependency in _dependencies(issue_body):
        if dependency not in known:
            findings.append(AuditFinding(
                "broken-dependency", "error", f"dependency {dependency!r} does not resolve to a known task_id"
            ))
    return findings


def _dependencies(issue_body: str) -> tuple[str, ...]:
    """Parse the intentionally small depends_on YAML subset used in task headers."""
    lines = issue_body.splitlines()
    for index, line in enumerate(lines):
        if line.strip().startswith("depends_on:"):
            inline = line.split(":", 1)[1].strip()
            if inline == "[]":
                return ()
            deps: list[str] = []
            for child in lines[index + 1:]:
                stripped = child.strip()
                if not child.startswith((" ", "\t")):
                    break
                if stripped.startswith("-"):
                    deps.append(stripped[1:].strip())
            return tuple(dep for dep in deps if dep)
    return ()


def duplicate_task_ids(issue_bodies: Iterable[str]) -> set[str]:
    counts = Counter(task_id for body in issue_bodies if (task_id := protocol_fields(body).get("task_id")))
    return {task_id for task_id, count in counts.items() if count > 1}


def reconcile_labels(issue_body: str, comments: Iterable[str], labels: Iterable[str], github_config: dict) -> set[str]:
    """Return the safe desired label set; never edits Issue comments/evidence."""
    unmanaged = {label for label in labels if not is_managed_label(label, github_config)}
    return unmanaged | desired_managed_labels(issue_body, comments, github_config)


def audit_snapshot(snapshot: Mapping[str, object], github_config: dict) -> dict:
    """Audit a portable GitHub-derived snapshot and return machine-readable results.

    Project state is intentionally optional. A missing Project API surface is reported as
    an informational boundary rather than fabricated as healthy or drifted state.
    """
    tasks = list(snapshot.get("tasks", []))
    bodies = [str(task.get("body", "")) for task in tasks]
    known_ids = {tid for body in bodies if (tid := protocol_fields(body).get("task_id"))}
    duplicates = duplicate_task_ids(bodies)
    results = []
    for task in tasks:
        findings = audit_task(
            issue_body=str(task.get("body", "")), comments=task.get("comments", []),
            labels=task.get("labels", []), github_config=github_config,
            issue_open=bool(task.get("open", True)), linked_pr_count=int(task.get("linked_pr_count", 0)),
            known_task_ids=known_ids,
        )
        tid = protocol_fields(str(task.get("body", ""))).get("task_id")
        if tid in duplicates:
            findings.append(AuditFinding("duplicate-task-id", "error", f"task_id {tid!r} appears more than once"))
        results.append({"issue": task.get("number"), "findings": [asdict(f) for f in findings]})

    global_findings: list[AuditFinding] = []
    topology = snapshot.get("scheduler_topology")
    if not isinstance(topology, Mapping) or not topology.get("recurring_orchestrator"):
        global_findings.append(AuditFinding("missing-recurring-reviewer", "error", "no recurring orchestrator/reviewer is observable"))
    if "project" not in snapshot:
        global_findings.append(AuditFinding("project-state-unavailable", "info", "Project field/membership state was not supplied; no Project drift conclusion made"))

    return {"tasks": results, "global_findings": [asdict(f) for f in global_findings]}
