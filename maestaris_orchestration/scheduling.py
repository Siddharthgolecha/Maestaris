"""Priority-first, dependency-aware scheduling helpers.

This module is a pure projection over already-reconstructed task metadata.  It never
changes canonical GitHub Issue state; callers remain responsible for ACK arbitration,
capability checks, and backpressure before claiming the selected task.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence


_PRIORITY = {"P0": 0, "P1": 1, "P2": 2}


@dataclass(frozen=True)
class SchedulingDecision:
    task_id: str | None
    explanation: str
    ranked: tuple[str, ...]
    blocked: tuple[str, ...]
    cycles: tuple[tuple[str, ...], ...]


def _cycle_nodes(graph: Mapping[str, tuple[str, ...]]) -> tuple[tuple[str, ...], ...]:
    """Return deterministic strongly-connected dependency cycles."""
    index = 0
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    low: dict[str, int] = {}
    cycles: list[tuple[str, ...]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = low[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)
        for dep in graph.get(node, ()):
            if dep not in graph:
                continue
            if dep not in indices:
                visit(dep)
                low[node] = min(low[node], low[dep])
            elif dep in on_stack:
                low[node] = min(low[node], indices[dep])
        if low[node] == indices[node]:
            component: list[str] = []
            while True:
                item = stack.pop()
                on_stack.remove(item)
                component.append(item)
                if item == node:
                    break
            component.sort()
            if len(component) > 1 or node in graph.get(node, ()):
                cycles.append(tuple(component))

    for node in sorted(graph):
        if node not in indices:
            visit(node)
    return tuple(sorted(cycles))


def scheduling_decision(
    tasks: Sequence[Mapping[str, object]],
    *,
    completed: Iterable[str] = (),
) -> SchedulingDecision:
    """Choose among eligible tasks with strict priority-first ordering.

    Required task keys are ``task_id`` and ``priority``. ``depends_on`` defaults to
    empty. ``age`` is an optional sortable value where smaller means older.  Tasks
    whose ``eligible`` value is false are retained as blocked diagnostics.

    Within one priority class, rank by recursive unblocking value, then downstream
    critical-path depth, then age, then task id. Dependencies absent from both the
    completed set and supplied task graph are unresolved and therefore block a task.
    Cycles are reported and every member of a cycle is blocked.
    """
    completed_set = set(completed)
    by_id = {str(t["task_id"]): t for t in tasks}
    graph = {
        task_id: tuple(str(x) for x in task.get("depends_on", ()) or ())
        for task_id, task in by_id.items()
    }
    cycles = _cycle_nodes(graph)
    cycle_members = {node for cycle in cycles for node in cycle}

    def deps_satisfied(task_id: str) -> bool:
        return all(dep in completed_set for dep in graph[task_id])

    blocked = {
        task_id
        for task_id, task in by_id.items()
        if task_id in cycle_members
        or not bool(task.get("eligible", True))
        or not deps_satisfied(task_id)
    }
    eligible = [task_id for task_id in by_id if task_id not in blocked]

    # Score the value of completing an eligible node by walking reverse dependency
    # edges. This is advisory only and cannot cross priority classes.
    reverse: dict[str, set[str]] = {task_id: set() for task_id in by_id}
    for child, deps in graph.items():
        for dep in deps:
            if dep in reverse:
                reverse[dep].add(child)

    def descendants(task_id: str) -> set[str]:
        seen: set[str] = set()
        todo = list(reverse.get(task_id, ()))
        while todo:
            node = todo.pop()
            if node in seen:
                continue
            seen.add(node)
            todo.extend(reverse.get(node, ()))
        return seen

    def depth(task_id: str, seen: frozenset[str] = frozenset()) -> int:
        if task_id in seen:
            return 0
        children = reverse.get(task_id, ())
        if not children:
            return 0
        next_seen = seen | {task_id}
        return 1 + max(depth(child, next_seen) for child in children)

    def key(task_id: str) -> tuple[object, ...]:
        task = by_id[task_id]
        priority = str(task.get("priority", "P2"))
        age = task.get("age", task_id)
        return (
            _PRIORITY.get(priority, 99),
            -len(descendants(task_id)),
            -depth(task_id),
            age,
            task_id,
        )

    ranked = tuple(sorted(eligible, key=key))
    if not ranked:
        explanation = "no eligible task; dependencies, cycle membership, or caller eligibility block all candidates"
        selected = None
    else:
        selected = ranked[0]
        task = by_id[selected]
        explanation = (
            f"selected {selected}: priority={task.get('priority', 'P2')} first; "
            f"unblocks={len(descendants(selected))}; critical_depth={depth(selected)}; "
            f"age={task.get('age', selected)!r}; deterministic task_id tie-break"
        )
    return SchedulingDecision(
        task_id=selected,
        explanation=explanation,
        ranked=ranked,
        blocked=tuple(sorted(blocked)),
        cycles=cycles,
    )
