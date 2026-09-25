"""Provider-neutral self-audit gate before a worker posts NEEDS_REVIEW."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True)
class PreReviewDecision:
    ready: bool
    blockers: tuple[str, ...]
    needs_refresh: bool = False


def pre_review_decision(
    *,
    completion: Mapping[str, bool],
    changed_paths: Sequence[str] = (),
    allowed_paths: Sequence[str] = (),
    head_sha: str | None = None,
    ci_available: bool = False,
    ci_head_sha: str | None = None,
    ci_success: bool = False,
    base_sha: str | None = None,
    current_main_sha: str | None = None,
    main_changed_paths: Sequence[str] | None = None,
    mergeable: bool | None = None,
    refresh_mechanical_safe: bool = False,
    semantic_conflict: bool = False,
) -> PreReviewDecision:
    """Fail closed on known completion, scope, CI, and integration-freshness gaps."""
    blockers: list[str] = []
    for criterion, satisfied in completion.items():
        if not satisfied:
            blockers.append(f"completion:{criterion}")

    if allowed_paths:
        allowed = tuple(p.rstrip("/") for p in allowed_paths)
        for path in changed_paths:
            if not any(path == p or path.startswith(p + "/") for p in allowed):
                blockers.append(f"scope:{path}")

    if ci_available:
        if not head_sha or ci_head_sha != head_sha:
            blockers.append("ci:not-exact-head")
        elif not ci_success:
            blockers.append("ci:not-successful")

    stale = bool(base_sha and current_main_sha and base_sha != current_main_sha)
    needs_refresh = False
    if stale:
        if semantic_conflict:
            blockers.append("integration:semantic-conflict")
        elif mergeable is False:
            blockers.append("integration:not-mergeable")
        elif main_changed_paths is None:
            blockers.append("integration:stale-unverified")
        else:
            overlap = sorted(set(changed_paths).intersection(main_changed_paths))
            if overlap:
                if refresh_mechanical_safe:
                    blockers.append("integration:refresh-required")
                    needs_refresh = True
                else:
                    blockers.append("integration:overlap-unverified")
            elif mergeable is not True:
                blockers.append("integration:mergeability-unverified")

    return PreReviewDecision(not blockers, tuple(blockers), needs_refresh)
