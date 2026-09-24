from __future__ import annotations

from typing import Iterable

from .protocol import protocol_fields, reduce_task_status, worker_from_event


def latest_ack(comments: Iterable[str]) -> dict[str, str]:
    """Return metadata from the latest ACK event, if any."""
    latest: dict[str, str] = {}
    for raw in comments:
        body = (raw or "").strip()
        if not body.startswith("[WORKER:"):
            continue
        fields = protocol_fields(body)
        if fields.get("status") != "ACK":
            continue
        latest = {
            "worker": worker_from_event(body) or "",
            "dispatcher": fields.get("dispatcher", ""),
            "runtime": fields.get("runtime", ""),
            "instance": fields.get("instance", ""),
            "claimed_at": fields.get("claimed_at", ""),
        }
    return {key: value for key, value in latest.items() if value}


def project_field_values(
    issue_body: str,
    comments: Iterable[str],
    field_sync: dict,
) -> dict[str, str]:
    """Derive optional GitHub Project field values from canonical Issue history."""
    comments = list(comments)
    fields = protocol_fields(issue_body)
    status = reduce_task_status(comments)
    ack = latest_ack(comments)

    values: dict[str, str] = {}

    priority = fields.get("priority")
    priority_map = ((field_sync.get("mappings") or {}).get("priority") or {})
    if priority:
        values["priority"] = str(priority_map.get(priority, priority))

    status_map = ((field_sync.get("mappings") or {}).get("status") or {})
    values["status"] = str(status_map.get(status, status))

    for key in ("worker", "dispatcher", "runtime"):
        if ack.get(key):
            values[key] = ack[key]

    return values
