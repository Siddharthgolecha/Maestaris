from maestaris_orchestration.checkpoints import Checkpoint, fingerprint_inputs, resume_decision

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
