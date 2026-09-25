"""Provider-neutral runtime failure classification for safe task recovery.

Runtime failures describe an invocation/runtime, not the substantive task result. The
caller may persist the returned reason in canonical Issue history when GitHub writes
remain available; otherwise normal ACK lease expiry is the recovery mechanism.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RuntimeFailureKind(str, Enum):
    PROVIDER_POLICY_REFUSAL = "provider-policy-refusal"
    TOOL_AUTH_DENIED = "tool-auth-denied"
    CAPABILITY_UNAVAILABLE = "capability-unavailable"
    PROVIDER_OUTAGE = "provider-outage"
    MALFORMED_OR_IRRELEVANT_REFUSAL = "malformed-or-irrelevant-refusal"


@dataclass(frozen=True)
class RuntimeFailure:
    kind: RuntimeFailureKind
    recoverable: bool = True
    substantive_task_failure: bool = False


def classify_runtime_failure(reason: str) -> RuntimeFailure:
    """Classify bounded invocation failure without changing the task conclusion.

    No branch here bypasses or weakens provider policy. A benign request incorrectly
    refused by one runtime remains the same task and may later be attempted only by a
    separately compatible runtime under its own controls.
    """

    text = reason.casefold()
    if any(token in text for token in ("401", "403", "unauthor", "forbidden", "auth denied")):
        kind = RuntimeFailureKind.TOOL_AUTH_DENIED
    elif any(token in text for token in ("capability", "tool unavailable", "not available")):
        kind = RuntimeFailureKind.CAPABILITY_UNAVAILABLE
    elif any(token in text for token in ("outage", "service unavailable", "timeout", "rate limit")):
        kind = RuntimeFailureKind.PROVIDER_OUTAGE
    elif any(token in text for token in ("policy", "safety", "refus")):
        kind = RuntimeFailureKind.PROVIDER_POLICY_REFUSAL
    else:
        kind = RuntimeFailureKind.MALFORMED_OR_IRRELEVANT_REFUSAL
    return RuntimeFailure(kind=kind)


def runtime_blocked_event(failure: RuntimeFailure) -> dict[str, object]:
    """Return machine-readable fields suitable for a bounded BLOCKED event."""

    return {
        "failure_scope": "runtime",
        "reason": failure.kind.value,
        "recoverable": failure.recoverable,
        "substantive_task_failure": failure.substantive_task_failure,
    }


def recovery_decision(
    failure: RuntimeFailure,
    *,
    ack_active: bool,
    github_writable: bool,
    phase: str = "work",
) -> str:
    """Choose the durable, provider-neutral recovery path for an invocation failure.

    ``phase`` is accepted for audit clarity (work/review) but deliberately does not
    alter task semantics. Before ACK there is no lease to release. After ACK, a runtime
    that can still write records a runtime-scoped BLOCKED event and releases ownership;
    otherwise the canonical lease simply expires. A later dispatcher must independently
    satisfy capability/admission rules before claiming the task.
    """

    del phase
    if not failure.recoverable:
        return "manual-orchestrator-review"
    if not ack_active:
        return "leave-unclaimed"
    if github_writable:
        return "record-runtime-blocked-and-release"
    return "await-lease-expiry"
