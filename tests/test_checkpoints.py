from maestaris_orchestration.checkpoints import (
    Checkpoint,
    fingerprint_inputs,
    regeneration_plan,
    resume_decision,
)


def test_legacy_task_without_checkpoint():
    decision = resume_decision(None, current_inputs={}, available_artifacts={})
    assert decision.reason == "no-checkpoint"


def test_changed_inputs_invalidate_checkpoint():
    checkpoint = Checkpoint("c1", "abc", fingerprint_inputs({"version": 1}), {}, True)
    decision = resume_decision(checkpoint, current_inputs={"version": 2}, available_artifacts={})
    assert decision.reason == "inputs-changed"


def test_verified_empty_checkpoint_can_resume():
    checkpoint = Checkpoint("c1", "abc", fingerprint_inputs({"version": 1}), {}, True)
    decision = resume_decision(checkpoint, current_inputs={"version": 1}, available_artifacts={})
    assert decision.reusable


def test_missing_source_commit_is_rejected():
    checkpoint = Checkpoint("c1", "missing", fingerprint_inputs({"version": 1}), {}, True)
    decision = resume_decision(
        checkpoint,
        current_inputs={"version": 1},
        available_artifacts={},
        source_commit_exists=False,
    )
    assert decision.reason == "source-commit-missing"


def test_missing_or_corrupt_artifact_is_rejected():
    digest = "0" * 64
    checkpoint = Checkpoint(
        "c1", "abc", fingerprint_inputs({"version": 1}), {"raw.bin": digest}, True
    )
    missing = resume_decision(
        checkpoint, current_inputs={"version": 1}, available_artifacts={}
    )
    corrupt = resume_decision(
        checkpoint,
        current_inputs={"version": 1},
        available_artifacts={"raw.bin": b"not-the-expected-content"},
    )
    assert missing.reason == "artifact-missing:raw.bin"
    assert corrupt.reason == "artifact-corrupt:raw.bin"


def test_presentation_failure_reuses_raw_artifacts():
    plan = regeneration_plan(
        raw_artifacts=("raw.csv",),
        derived_artifacts=("figure.png", "report.pdf"),
        reusable_artifacts=("raw.csv", "figure.png"),
        failed_stage="presentation",
    )
    assert plan == ("report.pdf",)
