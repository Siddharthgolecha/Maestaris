"""Deterministic execution routing with optional System-1 overlays.

The canonical task state remains GitHub Issue history.  This module only projects an
advisory execution plan.  External models may refine that plan, but they cannot weaken
hard capability floors or establish ownership/review state.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from typing import Any, Iterable, Mapping, Sequence


TIER_ORDER = ("deterministic", "small", "standard", "frontier")
_TIER_RANK = {name: index for index, name in enumerate(TIER_ORDER)}


def _tier(value: object) -> str:
    name = str(value or "").strip().lower()
    if name not in _TIER_RANK:
        raise ValueError(f"unknown execution tier: {value!r}")
    return name


def _max_tier(*values: str) -> str:
    return max((_tier(value) for value in values), key=_TIER_RANK.__getitem__)


def _step_up(value: str) -> str:
    rank = _TIER_RANK[_tier(value)]
    return TIER_ORDER[min(rank + 1, len(TIER_ORDER) - 1)]


@dataclass(frozen=True)
class TaskFeatures:
    task_id: str
    priority: str = "P2"
    requires_write: bool = False
    requires_code_generation: bool = False
    requires_formal_proof: bool = False
    scientific: bool = False
    high_risk: bool = False
    requires_external_network: bool = False
    context_chars: int = 0
    candidate_tools: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, value: Mapping[str, object]) -> "TaskFeatures":
        raw_tools = value.get("candidate_tools", ()) or ()
        if isinstance(raw_tools, str):
            raw_tools = (raw_tools,)
        return cls(
            task_id=str(value.get("task_id", "")).strip(),
            priority=str(value.get("priority", "P2")).strip() or "P2",
            requires_write=bool(value.get("requires_write", False)),
            requires_code_generation=bool(value.get("requires_code_generation", False)),
            requires_formal_proof=bool(value.get("requires_formal_proof", False)),
            scientific=bool(value.get("scientific", False)),
            high_risk=bool(value.get("high_risk", False)),
            requires_external_network=bool(value.get("requires_external_network", False)),
            context_chars=max(0, int(value.get("context_chars", 0) or 0)),
            candidate_tools=tuple(str(item) for item in raw_tools),
        )


@dataclass(frozen=True)
class RoutePlan:
    task_id: str
    minimum_tier: str
    selected_tier: str
    decision_source: str
    confidence: float | None
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class System1Signal:
    recommended_tier: str
    confidence: float
    needs_reasoning_probability: float | None = None
    complexity_score: float | None = None
    source: str = "system1"

    @classmethod
    def from_typed_answers(
        cls,
        answers: Mapping[str, object],
        *,
        source: str,
    ) -> "System1Signal":
        route = answers.get("route") or {}
        if not isinstance(route, Mapping):
            raise ValueError("route answer must be a mapping")
        recommended = _tier(route.get("choice"))
        confidence = float(route.get("confidence", 0.0) or 0.0)

        reasoning = answers.get("needs_reasoning")
        reasoning_probability: float | None = None
        if isinstance(reasoning, Mapping) and "noul" in reasoning:
            reasoning_probability = float(reasoning["noul"])

        complexity = answers.get("complexity")
        complexity_score: float | None = None
        if isinstance(complexity, Mapping) and "score" in complexity:
            complexity_score = float(complexity["score"])

        return cls(
            recommended_tier=recommended,
            confidence=max(0.0, min(1.0, confidence)),
            needs_reasoning_probability=reasoning_probability,
            complexity_score=complexity_score,
            source=source,
        )


def minimum_tier(features: TaskFeatures) -> tuple[str, tuple[str, ...]]:
    """Return the non-negotiable capability floor and its evidence."""
    floor = "deterministic"
    reasons: list[str] = []

    if features.candidate_tools or features.requires_external_network:
        floor = _max_tier(floor, "small")
        reasons.append("tool/network use requires at least a small execution lane")
    if features.requires_write or features.requires_code_generation or features.scientific:
        floor = _max_tier(floor, "standard")
        reasons.append("write/code/scientific work requires at least the standard lane")
    if features.requires_formal_proof or features.high_risk:
        floor = "frontier"
        reasons.append("formal-proof/high-risk work requires the frontier lane")
    if not reasons:
        reasons.append("task is compatible with deterministic execution")
    return floor, tuple(reasons)


def deterministic_route(
    features: TaskFeatures,
    *,
    long_context_chars: int = 20_000,
) -> RoutePlan:
    """Compute the reproducible zero-model baseline route.

    The baseline is intentionally conservative enough to run without Jev/Laya.  Priority
    is not used as a complexity proxy.
    """
    floor, reasons = minimum_tier(features)
    selected = floor
    extra: list[str] = list(reasons)

    if features.context_chars >= long_context_chars:
        selected = _max_tier(selected, "frontier")
        extra.append(
            f"context_chars={features.context_chars} crosses long-context threshold {long_context_chars}"
        )
    elif features.context_chars >= long_context_chars // 4:
        selected = _max_tier(selected, "standard")
        extra.append("medium context raises the default route to standard")

    return RoutePlan(
        task_id=features.task_id,
        minimum_tier=floor,
        selected_tier=selected,
        decision_source="deterministic",
        confidence=None,
        reasons=tuple(extra),
    )


def apply_system1_signal(
    baseline: RoutePlan,
    signal: System1Signal,
    *,
    upgrade_confidence: float = 0.65,
    downgrade_confidence: float = 0.90,
) -> RoutePlan:
    """Apply a Laya/Jev-style typed decision without weakening hard floors.

    Upgrades are cheap insurance and use a lower threshold.  Downgrades save cost but
    require stronger confidence.  Uncertain signals leave the deterministic plan intact.
    """
    requested = _tier(signal.recommended_tier)
    floor = _tier(baseline.minimum_tier)
    baseline_tier = _tier(baseline.selected_tier)

    if _TIER_RANK[requested] < _TIER_RANK[floor]:
        return replace(
            baseline,
            decision_source=f"{signal.source}:floor-rejected",
            confidence=signal.confidence,
            reasons=baseline.reasons
            + (f"System-1 requested {requested}, below hard floor {floor}; ignored",),
        )

    if _TIER_RANK[requested] > _TIER_RANK[baseline_tier]:
        if signal.confidence < upgrade_confidence:
            return replace(
                baseline,
                decision_source=f"{signal.source}:uncertain-upgrade",
                confidence=signal.confidence,
                reasons=baseline.reasons
                + (
                    f"upgrade {baseline_tier}->{requested} below confidence threshold "
                    f"{upgrade_confidence:.2f}; kept baseline",
                ),
            )
    elif _TIER_RANK[requested] < _TIER_RANK[baseline_tier]:
        if signal.confidence < downgrade_confidence:
            return replace(
                baseline,
                decision_source=f"{signal.source}:uncertain-downgrade",
                confidence=signal.confidence,
                reasons=baseline.reasons
                + (
                    f"downgrade {baseline_tier}->{requested} below confidence threshold "
                    f"{downgrade_confidence:.2f}; kept baseline",
                ),
            )

    selected = _max_tier(floor, requested)
    return RoutePlan(
        task_id=baseline.task_id,
        minimum_tier=floor,
        selected_tier=selected,
        decision_source=signal.source,
        confidence=signal.confidence,
        reasons=baseline.reasons
        + (
            f"System-1 selected {requested} at confidence {signal.confidence:.3f}",
        ),
    )


def verifier_escalation(plan: RoutePlan, verdict: str) -> RoutePlan:
    """Escalate one tier after a deterministic verifier failure."""
    normalized = str(verdict).strip().lower()
    if normalized in {"pass", "passed", "success", "green"}:
        return plan
    if normalized not in {"fail", "failed", "failure", "red"}:
        return replace(
            plan,
            reasons=plan.reasons + (f"verifier verdict {verdict!r} is non-terminal; no escalation",),
        )
    escalated = _step_up(plan.selected_tier)
    if escalated == plan.selected_tier:
        reason = "verifier failed but route is already frontier"
    else:
        reason = f"verifier failure escalated {plan.selected_tier}->{escalated}"
    return replace(
        plan,
        selected_tier=escalated,
        decision_source=f"{plan.decision_source}+verifier",
        reasons=plan.reasons + (reason,),
    )


@dataclass(frozen=True)
class ToolPlan:
    accepted: bool
    tools: tuple[dict[str, object], ...]
    confidence: float
    reason: str

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def bounded_tool_plan(
    needle_response: Mapping[str, object],
    *,
    allowlisted_tools: Iterable[str],
    minimum_confidence: float = 0.70,
) -> ToolPlan:
    """Validate a Needle3-shaped tool selection against a deterministic allowlist.

    Needle3 remains a selector only.  The host executor decides whether a validated call
    is actually executed.
    """
    allowed = {str(name) for name in allowlisted_tools}
    confidence = float(needle_response.get("confidence", 0.0) or 0.0)
    raw_calls = needle_response.get("function_calls", ()) or ()
    if not isinstance(raw_calls, Sequence) or isinstance(raw_calls, (str, bytes)):
        return ToolPlan(False, (), confidence, "function_calls is not a sequence")
    if confidence < minimum_confidence:
        return ToolPlan(
            False,
            (),
            confidence,
            f"Needle3 confidence {confidence:.3f} is below {minimum_confidence:.3f}",
        )

    calls: list[dict[str, object]] = []
    for raw in raw_calls:
        if not isinstance(raw, Mapping):
            return ToolPlan(False, (), confidence, "tool call is not a mapping")
        name = str(raw.get("name", "")).strip()
        if name not in allowed:
            return ToolPlan(False, (), confidence, f"tool {name!r} is not allowlisted")
        arguments = raw.get("arguments", {}) or {}
        if not isinstance(arguments, Mapping):
            return ToolPlan(False, (), confidence, f"tool {name!r} arguments are not a mapping")
        calls.append({"name": name, "arguments": dict(arguments)})
    if not calls:
        return ToolPlan(False, (), confidence, "Needle3 selected no executable tool")
    return ToolPlan(True, tuple(calls), confidence, "all calls are allowlisted and confidence-gated")


def system1_questions() -> dict[str, object]:
    """Jev/Laya-compatible routing questions."""
    return {
        "route": {
            "type": "choice",
            "instructions": "Which execution tier is sufficient for this task?",
            "criteria": {
                "deterministic": "Fixed rules, parsing, validation, or mechanical state transition; no generation",
                "small": "Bounded tool selection/extraction or simple generation with low reasoning depth",
                "standard": "Normal software/research implementation requiring multi-step reasoning",
                "frontier": "Formal proof, high-risk reasoning, long-context integration, or difficult architecture",
            },
        },
        "needs_reasoning": {
            "type": "noul",
            "instructions": "Does this task require deep multi-step reasoning rather than a mechanical decision?",
        },
        "complexity": {
            "type": "score",
            "instructions": "How demanding is this task overall?",
            "criteria": ["mechanical", "routine", "substantial", "frontier"],
        },
    }


def executor_envelope(
    *,
    repository: str,
    issue_number: int,
    branch: str,
    plan: RoutePlan,
    allowed_tools: Iterable[str],
    pr_number: int | None = None,
    expected_head_sha: str | None = None,
) -> dict[str, object]:
    """Build the provider-neutral payload handed to a write-capable executor."""
    payload: dict[str, object] = {
        "schema": 1,
        "repository": repository,
        "issue_number": int(issue_number),
        "task_id": plan.task_id,
        "branch": branch,
        "route": plan.as_dict(),
        "allowed_tools": sorted({str(item) for item in allowed_tools}),
    }
    if pr_number is not None:
        payload["pr_number"] = int(pr_number)
    if expected_head_sha:
        payload["expected_head_sha"] = str(expected_head_sha)
    return payload
