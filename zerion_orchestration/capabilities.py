from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


_LIST_FIELD_RE = re.compile(r"^([a-z][a-z0-9_]*):\s*(.*)$")


def _normalize(values: Iterable[str]) -> frozenset[str]:
    return frozenset(str(value).strip().lower() for value in values if str(value).strip())


def list_field(body: str, name: str) -> tuple[str, ...]:
    """Parse a small YAML-like scalar/list field from a Zerion protocol record.

    Supports `requires: [python, web]`, `requires: python`, and the ordinary
    indented list form. It deliberately does not parse arbitrary YAML: Issue
    history remains the protocol record and capability routing needs only a
    bounded string-list contract.
    """
    lines = (body or "").splitlines()
    for index, line in enumerate(lines):
        match = _LIST_FIELD_RE.match(line)
        if not match or match.group(1) != name:
            continue
        inline = match.group(2).strip()
        if inline:
            if inline == "[]":
                return ()
            if inline.startswith("[") and inline.endswith("]"):
                return tuple(
                    item.strip().strip("'\"")
                    for item in inline[1:-1].split(",")
                    if item.strip()
                )
            return (inline.strip("'\""),)

        values: list[str] = []
        for following in lines[index + 1 :]:
            if following and not following[0].isspace():
                break
            stripped = following.strip()
            if stripped.startswith("- "):
                values.append(stripped[2:].strip().strip("'\""))
            elif stripped and not stripped.startswith("#"):
                break
        return tuple(values)
    return ()


@dataclass(frozen=True)
class CapabilityDecision:
    eligible: bool
    missing: tuple[str, ...] = ()
    preferred_matches: tuple[str, ...] = ()
    preference_misses: tuple[str, ...] = ()
    reason: str = ""


def task_capabilities(issue_body: str) -> tuple[frozenset[str], frozenset[str]]:
    """Return normalized hard requirements and soft preferences for a task."""
    return _normalize(list_field(issue_body, "requires")), _normalize(
        list_field(issue_body, "prefers")
    )


def capability_decision(
    issue_body: str,
    available: Iterable[str] | None,
) -> CapabilityDecision:
    """Decide capability eligibility without making provider-quality judgments.

    Legacy tasks with no `requires` field remain eligible. A task with hard
    requirements is ineligible when the dispatcher has unknown capabilities:
    unknown must never be treated as proof of a hard capability. `prefers` is
    advisory only and cannot make an otherwise-compatible dispatcher ineligible.
    """
    required, preferred = task_capabilities(issue_body)
    if available is None:
        if required:
            missing = tuple(sorted(required))
            return CapabilityDecision(
                False,
                missing=missing,
                preference_misses=tuple(sorted(preferred)),
                reason="dispatcher capabilities are unknown for a task with hard requirements",
            )
        return CapabilityDecision(
            True,
            preference_misses=tuple(sorted(preferred)),
            reason="legacy/unconstrained task is eligible when capabilities are unknown",
        )

    have = _normalize(available)
    missing = tuple(sorted(required - have))
    matched = tuple(sorted(preferred & have))
    preference_misses = tuple(sorted(preferred - have))
    if missing:
        return CapabilityDecision(
            False,
            missing=missing,
            preferred_matches=matched,
            preference_misses=preference_misses,
            reason="dispatcher is missing hard task capabilities",
        )
    return CapabilityDecision(
        True,
        preferred_matches=matched,
        preference_misses=preference_misses,
        reason="all hard task capabilities are satisfied",
    )
