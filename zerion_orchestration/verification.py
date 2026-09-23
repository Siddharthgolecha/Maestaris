"""Pure evaluation of optional independent-verification policies.

Canonical task/review evidence remains in GitHub Issue history. This module only
projects a decision from already reconstructed records; it never mutates task state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class VerificationDecision:
    satisfied: bool
    accepted_reviewers: tuple[str, ...]
    reasons: tuple[str, ...]


def verification_decision(
    policy: Mapping[str, object] | None,
    records: Iterable[Mapping[str, object]],
    *,
    implementation_worker: str | None = None,
    implementation_runtime: str | None = None,
    ci_passed: bool | None = None,
    evidence_present: bool | None = None,
) -> VerificationDecision:
    """Evaluate a portable review policy against reconstructed verification records.

    No policy means legacy behavior: independent verification adds no gate. Supported
    policy keys are ``min_reviewers`` (default 1), ``different_worker``,
    ``different_runtime``, ``require_ci``, and ``require_evidence``. Only records with
    ``status: VERIFIED`` count. Duplicate reviewer identities count once.
    """
    if not policy:
        return VerificationDecision(True, (), ("legacy policy: no independent verification required",))

    minimum = max(1, int(policy.get("min_reviewers", 1)))
    different_worker = bool(policy.get("different_worker", False))
    different_runtime = bool(policy.get("different_runtime", False))
    reasons: list[str] = []
    accepted: dict[str, Mapping[str, object]] = {}

    for record in records:
        if str(record.get("status", "")) != "VERIFIED":
            continue
        reviewer = str(record.get("reviewer", "")).strip()
        if not reviewer:
            continue
        runtime = str(record.get("runtime", "")).strip() or None
        if different_worker and implementation_worker and reviewer == implementation_worker:
            continue
        if different_runtime and implementation_runtime and runtime == implementation_runtime:
            continue
        # Missing runtime cannot prove a different-runtime requirement.
        if different_runtime and implementation_runtime and runtime is None:
            continue
        accepted.setdefault(reviewer, record)

    if len(accepted) < minimum:
        reasons.append(f"need {minimum} independent reviewer(s); have {len(accepted)}")
    if bool(policy.get("require_ci", False)) and ci_passed is not True:
        reasons.append("required CI evidence is not passing")
    if bool(policy.get("require_evidence", False)) and evidence_present is not True:
        reasons.append("required durable evidence is missing")

    if not reasons:
        reasons.append("independent verification policy satisfied")
    return VerificationDecision(not any(r.startswith(("need ", "required ")) for r in reasons), tuple(sorted(accepted)), tuple(reasons))
