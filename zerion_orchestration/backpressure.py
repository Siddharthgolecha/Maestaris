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
    pending = False
    for body, fields in _events(comments):
        if body.startswith("[WORKER:") and fields.get("status") in TERMINAL and fields.get("dispatcher") == dispatcher:
            pending = True
        elif body.startswith("[ORCHESTRATOR-REVIEW:v1]") and fields.get("status") in REVIEWS:
            pending = False
    return pending


def revised_task_for_dispatcher(comments: Iterable[str], dispatcher: str) -> bool:
    owned = False
    revise = False
    for body, fields in _events(comments):
        if body.startswith("[WORKER:") and fields.get("dispatcher") == dispatcher:
            event = fields.get("status")
            if event in {"ACK", *TERMINAL}:
                owned = True
            if event == "ACK" and revise:
                revise = False
        elif body.startswith("[ORCHESTRATOR-REVIEW:v1]"):
            status = fields.get("status")
            if status == "REVISE" and owned:
                revise = True
            elif status in {"ACCEPTED", "REJECTED"}:
                revise = False
    return revise


def pending_review_tasks(histories: Mapping[str, Iterable[str]], dispatcher: str) -> tuple[str, ...]:
    return tuple(task_id for task_id, comments in histories.items() if pending_review_for_dispatcher(comments, dispatcher))


def revised_tasks(histories: Mapping[str, Iterable[str]], dispatcher: str) -> tuple[str, ...]:
    return tuple(task_id for task_id, comments in histories.items() if revised_task_for_dispatcher(comments, dispatcher))


def dispatcher_admission(histories: Mapping[str, Iterable[str]], dispatcher: str, max_pending_reviews: int) -> dict[str, object]:
    """Gate unrelated ACKs using canonical Issue histories.

    A REVISE must be resumed before unrelated work. Otherwise the configured pending
    review limit blocks new claims. Worker identity is irrelevant: accounting is by
    dispatcher, so multiple specialists sharing one scheduled dispatcher share capacity.
    """
    revised = revised_tasks(histories, dispatcher)
    pending = pending_review_tasks(histories, dispatcher)
    if revised:
        return {"allow_new": False, "resume": revised[0], "pending": pending, "reason": "resume-revise"}
    if len(pending) >= max_pending_reviews:
        return {"allow_new": False, "resume": None, "pending": pending, "reason": "pending-review-limit"}
    return {"allow_new": True, "resume": None, "pending": pending, "reason": "capacity-available"}


def mistaken_ack_recovery(comments: Iterable[str], dispatcher: str) -> str | None:
    """Preserve a mistaken ACK but stop before substantive execution."""
    for body, fields in reversed(list(_events(comments))):
        if body.startswith("[WORKER:") and fields.get("status") == "ACK" and fields.get("dispatcher") == dispatcher:
            return "stop-without-rewrite"
    return None
