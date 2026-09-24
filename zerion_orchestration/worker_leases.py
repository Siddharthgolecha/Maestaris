from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import math
from typing import Iterable

from .protocol import protocol_fields, worker_from_event


@dataclass(frozen=True)
class WorkerLeaseState:
    worker: str
    dispatcher: str
    claimed_at: datetime
    expires_at: datetime
    attempt: int


def _time(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _hours(value: str) -> float | None:
    try:
        hours = float(value)
    except (TypeError, ValueError):
        return None
    return hours if math.isfinite(hours) and hours > 0 else None


def _attempt(value: str, fallback: int) -> int:
    try:
        attempt = int(value)
    except (TypeError, ValueError):
        return fallback
    return attempt if attempt > 0 else fallback


def _dispatcher(fields: dict[str, str], *, worker: str, status: str) -> str:
    """Return a stable ownership identity, including pre-dispatcher ACK history.

    Modern ACK/RENEW events are required to carry dispatcher metadata.  The audit
    layer, however, predates that requirement and existing durable Issue history
    (and its compatibility tests) contains otherwise-valid ACK leases without a
    dispatcher.  Preserve those ACK intervals for expiry/retry projection instead
    of falsely declaring them expired immediately.  RENEW stays strict: a renewal
    without dispatcher metadata cannot extend ownership.
    """
    dispatcher = fields.get("dispatcher", "").strip()
    if dispatcher:
        return dispatcher
    if status == "ACK":
        return f"legacy:{worker}"
    return ""


def active_worker_lease(
    comments: Iterable[str], now: datetime | None = None
) -> WorkerLeaseState | None:
    """Project the authoritative unexpired worker ACK/renewal lease.

    A competing ACK cannot steal an unexpired lease. The current owner may renew it,
    but stale/shorter renewals never rewind the interval. Terminal worker reports and
    orchestrator reviews consume ownership. Expired leases are simply absent, making
    the task recoverable without rewriting history.
    """
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    active: WorkerLeaseState | None = None
    next_attempt = 1

    for raw in comments:
        body = (raw or "").strip()
        fields = protocol_fields(body)
        if body.startswith("[WORKER:") and fields.get("status") in {"ACK", "RENEW"}:
            status = fields.get("status", "")
            worker = worker_from_event(body)
            dispatcher = _dispatcher(fields, worker=worker or "", status=status)
            claimed_at = _time(fields.get("claimed_at", ""))
            hours = _hours(fields.get("lease_hours", ""))
            if not worker or not dispatcher or claimed_at is None or hours is None:
                continue
            if claimed_at > now:
                continue
            try:
                expires_at = claimed_at + timedelta(hours=hours)
            except OverflowError:
                continue

            attempt = _attempt(fields.get("attempt", ""), next_attempt)
            candidate = WorkerLeaseState(worker, dispatcher, claimed_at, expires_at, attempt)
            if active is not None and active.expires_at > claimed_at:
                same_owner = worker == active.worker and dispatcher == active.dispatcher
                if same_owner and claimed_at >= active.claimed_at and expires_at > active.expires_at:
                    active = candidate
                continue
            active = candidate
            next_attempt = max(next_attempt, attempt + 1)

        elif body.startswith("[WORKER:") and fields.get("status") in {
            "DONE", "BLOCKED", "NEEDS_REVIEW"
        }:
            active = None
        elif body.startswith("[ORCHESTRATOR-REVIEW:v1]"):
            active = None

    if active is None or active.expires_at <= now:
        return None
    return active


def retry_count(comments: Iterable[str]) -> int:
    """Count accepted ownership attempts, not harmless polling/renewal traffic.

    A compatibility ACK from the current owner while its lease is still active is a
    renewal, not a retry. Competing ACKs inside that active interval are ignored too.
    A new ACK counts only after the prior lease has expired or ownership was consumed
    by a terminal worker/orchestrator event.
    """
    count = 0
    active: WorkerLeaseState | None = None
    seen: set[tuple[str, str, str]] = set()

    for raw in comments:
        body = (raw or "").strip()
        fields = protocol_fields(body)
        if body.startswith("[WORKER:") and fields.get("status") in {"ACK", "RENEW"}:
            status = fields.get("status", "")
            worker = worker_from_event(body)
            dispatcher = _dispatcher(fields, worker=worker or "", status=status)
            claimed_at = _time(fields.get("claimed_at", ""))
            hours = _hours(fields.get("lease_hours", ""))
            if not worker or not dispatcher or claimed_at is None or hours is None:
                continue
            try:
                expires_at = claimed_at + timedelta(hours=hours)
            except OverflowError:
                continue
            key = (worker, dispatcher, fields.get("claimed_at", "").strip())
            if key in seen:
                continue
            seen.add(key)

            if active is not None and active.expires_at > claimed_at:
                same_owner = worker == active.worker and dispatcher == active.dispatcher
                if same_owner and claimed_at >= active.claimed_at and expires_at > active.expires_at:
                    active = WorkerLeaseState(worker, dispatcher, claimed_at, expires_at, active.attempt)
                continue

            # RENEW without an active lease cannot create a retry attempt. It is stale
            # renewal traffic and must not consume the retry budget.
            if status == "RENEW":
                continue
            count += 1
            active = WorkerLeaseState(worker, dispatcher, claimed_at, expires_at, count)

        elif body.startswith("[WORKER:") and fields.get("status") in {
            "DONE", "BLOCKED", "NEEDS_REVIEW"
        }:
            active = None
        elif body.startswith("[ORCHESTRATOR-REVIEW:v1]"):
            active = None

    return count


def recovery_state(
    comments: Iterable[str], *, retry_budget: int, now: datetime | None = None
) -> str:
    """Return claimed, ready, or quarantine from durable history.

    Quarantine is a derived holding state: it preserves all prior failure evidence and
    requires an orchestrator decision rather than cycling forever.
    """
    if active_worker_lease(comments, now=now) is not None:
        return "claimed"
    attempts = retry_count(comments)
    if retry_budget >= 0 and attempts >= retry_budget and attempts > 0:
        return "quarantine"
    return "ready"
