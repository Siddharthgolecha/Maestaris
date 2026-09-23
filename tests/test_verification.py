from zerion_orchestration.verification import verification_decision


def verified(reviewer, runtime):
    return {"status": "VERIFIED", "reviewer": reviewer, "runtime": runtime}


def test_legacy_task_has_no_new_gate():
    assert verification_decision(None, []).satisfied


def test_same_runtime_cannot_satisfy_different_runtime_policy():
    policy = {"min_reviewers": 1, "different_runtime": True}
    decision = verification_decision(
        policy,
        [verified("reviewer-b", "chatgpt")],
        implementation_worker="worker-a",
        implementation_runtime="chatgpt",
    )
    assert not decision.satisfied
    assert decision.accepted_reviewers == ()


def test_different_runtime_verification_satisfies_policy():
    policy = {"min_reviewers": 1, "different_runtime": True}
    decision = verification_decision(
        policy,
        [verified("reviewer-b", "gemini-spark")],
        implementation_worker="worker-a",
        implementation_runtime="chatgpt",
    )
    assert decision.satisfied
    assert decision.accepted_reviewers == ("reviewer-b",)


def test_same_worker_cannot_self_verify_when_independence_required():
    policy = {"min_reviewers": 1, "different_worker": True}
    assert not verification_decision(
        policy,
        [verified("worker-a", "gemini-spark")],
        implementation_worker="worker-a",
        implementation_runtime="chatgpt",
    ).satisfied


def test_duplicate_reviewer_counts_once_and_nonverified_records_do_not_count():
    policy = {"min_reviewers": 2}
    records = [
        verified("r1", "chatgpt"),
        verified("r1", "gemini-spark"),
        {"status": "COMMENT", "reviewer": "r2", "runtime": "claude"},
    ]
    assert not verification_decision(policy, records).satisfied


def test_ci_and_durable_evidence_requirements_are_explicit():
    policy = {"min_reviewers": 1, "require_ci": True, "require_evidence": True}
    records = [verified("r1", "gemini-spark")]
    assert not verification_decision(policy, records, ci_passed=True, evidence_present=False).satisfied
    assert verification_decision(policy, records, ci_passed=True, evidence_present=True).satisfied


def test_missing_runtime_cannot_prove_runtime_independence():
    policy = {"different_runtime": True}
    assert not verification_decision(
        policy,
        [{"status": "VERIFIED", "reviewer": "r1"}],
        implementation_runtime="chatgpt",
    ).satisfied


def test_missing_implementation_runtime_cannot_prove_runtime_independence():
    policy = {"different_runtime": True}
    decision = verification_decision(policy, [verified("r1", "gemini-spark")])
    assert not decision.satisfied
    assert decision.accepted_reviewers == ()
    assert "required implementation runtime baseline is missing" in decision.reasons


def test_missing_implementation_worker_cannot_prove_worker_independence():
    policy = {"different_worker": True}
    decision = verification_decision(policy, [verified("r1", "gemini-spark")])
    assert not decision.satisfied
    assert decision.accepted_reviewers == ()
    assert "required implementation worker baseline is missing" in decision.reasons
