"""Verified optional task checkpoints; never ownership or terminal state."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib, json
from typing import Mapping, Sequence

@dataclass(frozen=True)
class Checkpoint:
    checkpoint_id: str
    source_commit: str
    input_fingerprint: str
    artifacts: Mapping[str, str]
    verified: bool = False

@dataclass(frozen=True)
class ResumeDecision:
    reusable: bool
    reason: str
    reusable_artifacts: tuple[str, ...] = ()

def fingerprint_inputs(inputs: Mapping[str, object]) -> str:
    payload = json.dumps(inputs, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()

def verify_artifact(content: bytes, expected_sha256: str) -> bool:
    if len(expected_sha256) != 64:
        return False
    try:
        int(expected_sha256, 16)
    except ValueError:
        return False
    return hashlib.sha256(content).hexdigest() == expected_sha256.lower()

def resume_decision(checkpoint: Checkpoint | None, *, current_inputs: Mapping[str, object],
                    available_artifacts: Mapping[str, bytes], source_commit_exists: bool = True) -> ResumeDecision:
    if checkpoint is None:
        return ResumeDecision(False, "no-checkpoint")
    if not checkpoint.verified:
        return ResumeDecision(False, "checkpoint-not-verified")
    if not source_commit_exists:
        return ResumeDecision(False, "source-commit-missing")
    if checkpoint.input_fingerprint != fingerprint_inputs(current_inputs):
        return ResumeDecision(False, "inputs-changed")
    names = []
    for name, digest in sorted(checkpoint.artifacts.items()):
        content = available_artifacts.get(name)
        if content is None:
            return ResumeDecision(False, f"artifact-missing:{name}")
        if not verify_artifact(content, digest):
            return ResumeDecision(False, f"artifact-corrupt:{name}")
        names.append(name)
    return ResumeDecision(True, "verified", tuple(names))

def regeneration_plan(*, raw_artifacts: Sequence[str], derived_artifacts: Sequence[str],
                      reusable_artifacts: Sequence[str], failed_stage: str) -> tuple[str, ...]:
    reusable = set(reusable_artifacts)
    if failed_stage in {"presentation", "packaging"}:
        return tuple(x for x in derived_artifacts if x not in reusable)
    return tuple(x for x in (*raw_artifacts, *derived_artifacts) if x not in reusable)
