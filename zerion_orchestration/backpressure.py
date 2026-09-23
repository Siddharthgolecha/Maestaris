from __future__ import annotations

from collections.abc import Iterable, Mapping

from .protocol import protocol_fields

TERMINAL = {"DONE", "BLOCKED", "NEEDS_REVIEW"}
REVIEWS = {"ACCEPTED", "REVISE", "REJECTED"}


def _events(comments: Iterable[str]):
    for raw in comments:
        body = (raw or "").strip()
        yield body, protocol_fields(body)


def pending_review_for_dispatcher(comments: Iterable[str], dispatcher: str) -> bool:
    """Whether this task has this dispatcher's terminal result awaiting review."""
    pending = False
    for body, fields in _events(comments):
        if body.startswith("[WORKER:"):
            if fields.get("status") in TERMINAL and fields.get("dispatcher") == dispatcher:
                pending = True
        elif body.startswith("[ORCHESTRATOR-REVIEW:v1]") and fields.get("status") in REVIEWS:
            pending = False
    return pending


def revised_task_for_dispatcher(comments: Iterable[str], dispatcher: str) -> bool:
    """Whether the latest review requires this dispatcher to resume its task."""
    owned = False
    revise = False
    for body, fields in _events(comments):
        if body.startswith("[WORKER:") and fields.get("dispatcher") == dispatcher:
            if fields.get("status") in {"ACK", *TERMINAL}:
                owned = True
        elif body.startswith("[ORCHESTRATOR-REVIEW:v1]"):
            status = fields.get("status")
            if status == "REVISE" and owned:
                revise = True
            elif status in {"ACCEPTED", "REJECTED"}:
                revise = False
        elif body.startswith("[WORKER:") and fields.get("dispatcher") == dispatcher:
            if fields.get("status") == "ACK" and revise:
                # The revised task has been resumed; it remains the dispatcher's work,
                # but should not be counted as an unreviewed terminal result.
                revise = False
    return revise


def pending_review_tasks(
    histories: Mapping[str, Iterable[str]], dispatcher: str
) -> tuple[str, ...]:
    return tuple(
        task_id
        for task_id, comments in histories.items()
        if pending_review_for_dispatcher(comments, dispatcher)
    )


def revised_tasks(
    histories: Mapping[str, Iterable[str]], dispatcher: str
) -> tuple[str, ...]:
    return tuple(
        task_id
        for task_id, comments in histories.items()
        if revised_task_for_dispatcher(comments, dispatcher)
    )


def dispatcher_admission(
    histories: Mapping[str, Iterable[str]],
    dispatcher: str,
    max_pending_reviews: int,
) -> dict[str, object]:
    """Pure admission gate to apply before ACKing unrelated READY work.

    REVISE resumption has precedence. Otherwise an at-capacity pending-review queue
    blocks new claims. The returned explanation is suitable for deterministic tests
    and conversational/scheduled dispatchers.
    """
    revised = revised_tasks(histories, dispatcher)
    pending = pending_review_tasks(histories, dispatcher)
    if revised:
        return {"allow_new": False, "resume": revised[0], "pending": pending, "reason": "resume-revise"}
    if len(pending) >= max_pending_reviews:
        return {"allow_new": False, "resume": None, "pending": pending, "reason": "pending-review-limit"}
    return {"allow_new": True, "resume": None, "pending": pending, "reason": "capacity-available"}


def mistaken_ack_recovery(comments: Iterable[str], dispatcher: str) -> str | None:
    """Return the safe action for an ACK posted while backpressure should block it.

    Canonical history is never rewritten: leave the mistaken ACK in place and stop
    before substantive execution. The orchestrator can review/reconcile it explicitly.
    """
    for body, fields in reversed(list(_events(comments))):
        if body.startswith("[WORKER:") and fields.get("status") == "ACK" and fields.get("dispatcher") == dispatcher:
            return "stop-without-rewrite"
    return None
