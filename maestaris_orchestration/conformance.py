"""Provider-neutral conformance checks for recorded Maestaris histories."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

WORKER_INVARIANTS = (
    "ack-arbitration", "dependencies", "hard-capabilities", "admission",
    "review-backpressure", "revise-resumption", "lease-expiry", "no-duplicate-work",
)
ORCHESTRATOR_INVARIANTS = (
    "review-claim-arbitration", "review-claim-expiry", "evidence-inspection",
    "no-merge-before-acceptance",
)
RUNTIME_INVARIANTS = (
    "provider-refusal-recovery", "tool-auth-recovery", "outage-recovery",
    "malformed-response-recovery",
)
ALL_INVARIANTS = WORKER_INVARIANTS + ORCHESTRATOR_INVARIANTS + RUNTIME_INVARIANTS

@dataclass(frozen=True)
class Observation:
    invariant: str
    passed: bool
    evidence: str = ""

@dataclass(frozen=True)
class ConformanceResult:
    runtime: str
    passed: tuple[str, ...]
    failed: tuple[str, ...]
    evidence: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    advisory: bool = True

    @property
    def compliant(self) -> bool:
        return not self.failed

    def as_dict(self) -> dict[str, object]:
        return {"schema": 1, "runtime": self.runtime, "advisory": True,
                "compliant": self.compliant, "passed": list(self.passed),
                "failed": list(self.failed),
                "evidence": {k: list(v) for k, v in self.evidence.items()}}

def evaluate(runtime: str, observations: Iterable[Observation], *, require_all: bool = True) -> ConformanceResult:
    grouped: dict[str, list[Observation]] = {}
    for obs in observations:
        if obs.invariant not in ALL_INVARIANTS:
            raise ValueError(f"unknown invariant: {obs.invariant}")
        grouped.setdefault(obs.invariant, []).append(obs)
    required = ALL_INVARIANTS if require_all else tuple(grouped)
    passed, failed, evidence = [], [], {}
    for invariant in required:
        rows = grouped.get(invariant, [])
        ok = bool(rows) and all(row.passed for row in rows)
        (passed if ok else failed).append(invariant)
        evidence[invariant] = tuple(row.evidence for row in rows if row.evidence)
    return ConformanceResult(runtime, tuple(passed), tuple(failed), evidence)

def compliant_recorded_scenario() -> tuple[Observation, ...]:
    return tuple(Observation(name, True, "deterministic compliant transcript") for name in ALL_INVARIANTS)

def gemini_backpressure_violation_scenario() -> tuple[Observation, ...]:
    return tuple(Observation(
        name, name != "review-backpressure",
        "claimed new work with exhausted pending-review capacity"
        if name == "review-backpressure" else "baseline invariant satisfied",
    ) for name in ALL_INVARIANTS)

def runtime_failure_scenario(kind: str, *, recovered_by_compatible_runtime: bool) -> tuple[Observation, ...]:
    mapping = {
        "provider-policy-refusal": "provider-refusal-recovery",
        "tool-auth-denied": "tool-auth-recovery",
        "provider-outage": "outage-recovery",
        "malformed-or-irrelevant-refusal": "malformed-response-recovery",
    }
    if kind not in mapping:
        raise ValueError(f"unsupported runtime failure kind: {kind}")
    return (Observation(mapping[kind], recovered_by_compatible_runtime, kind),)

def observations_from_mapping(rows: Sequence[Mapping[str, object]]) -> tuple[Observation, ...]:
    return tuple(Observation(str(r["invariant"]), bool(r["passed"]), str(r.get("evidence", ""))) for r in rows)
