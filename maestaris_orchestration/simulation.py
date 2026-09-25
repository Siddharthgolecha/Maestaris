"""Deterministic simulation helpers for Maestaris orchestration histories.

The simulator deliberately consumes the same durable comment strings that form the
GitHub control plane.  It is an invariant checker, not an alternate state store.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Mapping

from .protocol import protocol_fields


@dataclass(frozen=True)
class Violation:
    invariant: str
    task_id: str
    detail: str


def _time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def _lease_end(fields: Mapping[str, str]) -> datetime | None:
    start = _time(fields.get("claimed_at"))
    try:
        hours = float(fields.get("lease_hours", ""))
    except ValueError:
        return None
    return start + timedelta(hours=hours) if start is not None and hours > 0 else None


def invariant_violations(histories: Mapping[str, Iterable[str]], *, now: datetime) -> tuple[Violation, ...]:
    """Check safety invariants over recorded Issue histories at ``now``.

    The projection is intentionally conservative: malformed events are ignored rather
    than promoted into ownership.  Terminal evidence is retained and never mutated.
    """
    out: list[Violation] = []
    for task_id, comments in histories.items():
        worker_leases: list[tuple[str, datetime]] = []
        review_leases: list[tuple[str, datetime]] = []
        terminal_seen = False
        accepted = False
        for raw in comments:
            body = (raw or "").strip()
            fields = protocol_fields(body)
            status = fields.get("status")
            if body.startswith("[WORKER:"):
                if status in {"ACK", "RENEW"}:
                    owner = fields.get("dispatcher") or body.split(":", 2)[1]
                    end = _lease_end(fields)
                    start = _time(fields.get("claimed_at"))
                    if owner and end and start and start <= now < end:
                        worker_leases.append((owner, end))
                elif status in {"DONE", "BLOCKED", "NEEDS_REVIEW"}:
                    terminal_seen = True
            elif body.startswith("[ORCHESTRATOR-CLAIM:v1]"):
                owner = fields.get("orchestrator")
                end = _lease_end(fields)
                start = _time(fields.get("claimed_at"))
                if owner and end and start and start <= now < end:
                    review_leases.append((owner, end))
            elif body.startswith("[ORCHESTRATOR-REVIEW:v1]"):
                if status == "ACCEPTED":
                    accepted = True

        worker_owners = {owner for owner, _ in worker_leases}
        review_owners = {owner for owner, _ in review_leases}
        if len(worker_owners) > 1:
            out.append(Violation("single-worker-owner", task_id, repr(sorted(worker_owners))))
        if len(review_owners) > 1:
            out.append(Violation("single-review-owner", task_id, repr(sorted(review_owners))))
        if accepted and not terminal_seen:
            out.append(Violation("acceptance-requires-terminal-evidence", task_id, "ACCEPTED without worker terminal evidence"))
    return tuple(out)


def conformance_report(histories: Mapping[str, Iterable[str]], *, now: datetime) -> dict[str, object]:
    """Return stable machine-readable advisory evidence for simulation/conformance reuse."""
    violations = invariant_violations(histories, now=now)
    return {
        "schema": 1,
        "canonical_source": "github-issue-history",
        "passed": not violations,
        "violations": [
            {"invariant": v.invariant, "task_id": v.task_id, "detail": v.detail}
            for v in violations
        ],
    }
