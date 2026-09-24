"""Pure fair-share and named-resource admission decisions.

Canonical ownership/resource evidence remains in GitHub Issue history. This module
only projects whether an otherwise eligible task may ACK now.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class AdmissionDecision:
    admitted: bool
    reasons: tuple[str, ...]


def admission_decision(
    task: Mapping[str, object],
    active: Iterable[Mapping[str, object]],
    *,
    fair_share_limits: Mapping[str, int] | None = None,
    resource_limits: Mapping[str, int] | None = None,
) -> AdmissionDecision:
    """Evaluate optional same-priority fair share and named resource limits.

    Callers apply normal priority/dependency/capability/ownership gates first.
    ``active`` contains unexpired canonical leases. Missing configuration preserves
    legacy behavior. Resource leases therefore recover when their owning ACK expires.
    """
    fair_share_limits = fair_share_limits or {}
    resource_limits = resource_limits or {}
    active = tuple(active)
    reasons: list[str] = []

    group = str(task.get("fair_share_group", "")).strip()
    if group and group in fair_share_limits:
        limit = max(0, int(fair_share_limits[group]))
        priority = str(task.get("priority", ""))
        used = sum(
            1 for lease in active
            if str(lease.get("fair_share_group", "")).strip() == group
            and str(lease.get("priority", "")) == priority
        )
        if used >= limit:
            reasons.append(f"fair-share group {group!r} is full ({used}/{limit})")

    requested = task.get("resources", {}) or {}
    if not isinstance(requested, Mapping):
        reasons.append("resources must be a mapping")
        requested = {}
    for name, raw_slots in sorted(requested.items(), key=lambda item: str(item[0])):
        resource = str(name).strip()
        if not resource:
            reasons.append("resource name must be non-empty")
            continue
        slots = max(0, int(raw_slots))
        if resource not in resource_limits:
            reasons.append(f"resource {resource!r} has no configured limit")
            continue
        limit = max(0, int(resource_limits[resource]))
        used = 0
        for lease in active:
            lease_resources = lease.get("resources", {}) or {}
            if isinstance(lease_resources, Mapping):
                used += max(0, int(lease_resources.get(resource, 0)))
        if used + slots > limit:
            reasons.append(
                f"resource {resource!r} would exceed limit ({used}+{slots}>{limit})"
            )

    return AdmissionDecision(not reasons, tuple(reasons or ("admission available",)))
