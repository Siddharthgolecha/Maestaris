"""Provider-neutral dispatcher selection and terminal-report gates."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from .admission import admission_decision
from .pre_review import PreReviewDecision, pre_review_decision
from .scheduling import scheduling_decision


@dataclass(frozen=True)
class DispatcherDecision:
    task_id: str | None
    denied: tuple[str, ...]
    explanation: str


def dispatcher_selection(
    tasks: Sequence[Mapping[str, object]],
    *,
    completed: Iterable[str] = (),
    active: Iterable[Mapping[str, object]] = (),
    fair_share_limits: Mapping[str, int] | None = None,
    resource_limits: Mapping[str, int] | None = None,
    served: Mapping[str, int] | None = None,
    eligible_groups: Iterable[str] = (),
) -> DispatcherDecision:
    """Select the first schedulable task that may pass admission before ACK."""
    active = tuple(active)
    ranked = scheduling_decision(tasks, completed=completed)
    if not ranked.ranked:
        return DispatcherDecision(None, (), ranked.explanation)

    by_id = {str(task["task_id"]): task for task in tasks}
    top_priority = str(by_id[ranked.ranked[0]].get("priority", "P2"))
    denied: list[str] = []
    for task_id in ranked.ranked:
        task = by_id[task_id]
        if str(task.get("priority", "P2")) != top_priority:
            break
        admission = admission_decision(
            task,
            active,
            fair_share_limits=fair_share_limits,
            resource_limits=resource_limits,
            served=served,
            eligible_groups=eligible_groups,
        )
        if admission.admitted:
            return DispatcherDecision(task_id, tuple(denied), f"selected {task_id} after scheduling and pre-ACK admission")
        denied.append(task_id)

    return DispatcherDecision(None, tuple(denied), f"highest eligible priority {top_priority} has no admissible candidate; lower priorities remain blocked")


def terminal_review_gate(**evidence: object) -> PreReviewDecision:
    """Dispatcher-facing gate that must pass before emitting NEEDS_REVIEW."""
    return pre_review_decision(**evidence)  # type: ignore[arg-type]
