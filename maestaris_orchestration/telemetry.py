from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable

from .protocol import protocol_fields, reduce_task_status, worker_from_event


def _time(value: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class LifecycleEvent:
    index: int
    kind: str
    status: str
    task_id: str | None
    worker: str | None
    dispatcher: str | None
    runtime: str | None
    occurred_at: str | None
    trace_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def project_lifecycle_events(comments: Iterable[object], *, trace_id: str | None = None) -> list[LifecycleEvent]:
    """Project machine-readable telemetry from canonical comments without mutating them."""
    out: list[LifecycleEvent] = []
    for index, raw in enumerate(comments):
        if isinstance(raw, str):
            body, created_at = raw, None
        else:
            body = str((raw or {}).get("body", ""))
            created_at = (raw or {}).get("created_at")
        fields = protocol_fields(body)
        if body.strip().startswith("[WORKER:"):
            status, kind = fields.get("status", ""), "worker"
            worker = worker_from_event(body)
        elif body.strip().startswith("[ORCHESTRATOR-REVIEW:v1]"):
            status, kind, worker = fields.get("status", ""), "review", None
        else:
            continue
        occurred = fields.get("claimed_at") or created_at
        out.append(LifecycleEvent(index, kind, status, fields.get("task_id"), worker,
                                  fields.get("dispatcher"), fields.get("runtime"),
                                  occurred, trace_id))
    return out


def lifecycle_metrics(comments: Iterable[object], *, issue_created_at: str | None = None,
                      now: datetime | None = None) -> dict:
    """Derive operational metrics solely from durable GitHub history."""
    raw = list(comments)
    events = project_lifecycle_events(raw)
    bodies = [x if isinstance(x, str) else str((x or {}).get("body", "")) for x in raw]
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    ack = [e for e in events if e.status == "ACK"]
    terminal = [e for e in events if e.status in {"DONE", "BLOCKED", "NEEDS_REVIEW"}]
    reviews = [e for e in events if e.kind == "review"]
    checkpoints = [e for e in events if e.status == "CHECKPOINT"]

    def when(e: LifecycleEvent) -> datetime | None:
        return _time(e.occurred_at or "")

    created = _time(issue_created_at or "")
    first_ack = next((when(e) for e in ack if when(e)), None)
    first_terminal = next((when(e) for e in terminal if when(e)), None)
    first_review = next((when(e) for e in reviews if when(e)), None)

    expiries = 0
    collisions = 0
    active_until: datetime | None = None
    active_owner: tuple[str | None, str | None] | None = None
    for e in events:
        if e.status not in {"ACK", "RENEW"}:
            if e.status in {"DONE", "BLOCKED", "NEEDS_REVIEW"} or e.kind == "review":
                active_until = None
                active_owner = None
            continue
        t = when(e)
        if t is None:
            continue
        if active_until is not None and t >= active_until:
            expiries += 1
            active_until = active_owner = None
        owner = (e.worker, e.dispatcher)
        if active_until is not None and t < active_until and owner != active_owner:
            collisions += 1
            continue
        fields = protocol_fields(bodies[e.index])
        try:
            hours = float(fields.get("lease_hours", "0"))
        except ValueError:
            hours = 0
        if hours > 0:
            active_until = t + timedelta(hours=hours)
            active_owner = owner
    if active_until is not None and now >= active_until:
        expiries += 1

    def seconds(a: datetime | None, b: datetime | None) -> float | None:
        return None if a is None or b is None else max(0.0, (b - a).total_seconds())

    activity: dict[str, int] = {}
    for e in events:
        key = "/".join(x for x in (e.runtime, e.dispatcher) if x)
        if key:
            activity[key] = activity.get(key, 0) + 1

    return {
        "canonical_status": reduce_task_status(bodies),
        "queue_latency_seconds": seconds(created, first_ack),
        "cycle_latency_seconds": seconds(first_ack, first_terminal),
        "review_latency_seconds": seconds(first_terminal, first_review),
        "retries": max(0, len(ack) - 1),
        "collisions": collisions,
        "lease_expiries": expiries,
        "checkpoints": len(checkpoints),
        "activity": activity,
        "event_count": len(events),
    }


def export_payload(comments: Iterable[object], *, issue_created_at: str | None = None,
                   trace_id: str | None = None) -> dict:
    """Return a credential-free adapter payload suitable for webhook/OTel bridges."""
    raw = list(comments)
    return {
        "schema": 1,
        "trace_id": trace_id,
        "events": [e.to_dict() for e in project_lifecycle_events(raw, trace_id=trace_id)],
        "metrics": lifecycle_metrics(raw, issue_created_at=issue_created_at),
    }
