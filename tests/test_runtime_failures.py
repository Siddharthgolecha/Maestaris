from maestaris_orchestration.runtime_failures import (
    RuntimeFailureKind,
    classify_runtime_failure,
    recovery_decision,
    runtime_blocked_event,
)


def test_refusal_before_ack_is_recoverable_without_substantive_failure():
    failure = classify_runtime_failure("provider safety policy refusal")
    assert failure.kind is RuntimeFailureKind.PROVIDER_POLICY_REFUSAL
    assert recovery_decision(failure, ack_active=False, github_writable=True) == "leave-unclaimed"
    assert failure.substantive_task_failure is False


def test_refusal_after_ack_records_runtime_block_and_releases_for_failover():
    failure = classify_runtime_failure("403 tool auth denied")
    event = runtime_blocked_event(failure)
    assert event == {
        "failure_scope": "runtime",
        "reason": "tool-auth-denied",
        "recoverable": True,
        "substantive_task_failure": False,
    }
    assert recovery_decision(failure, ack_active=True, github_writable=True) == "record-runtime-blocked-and-release"


def test_refusal_after_ack_without_github_write_uses_lease_expiry():
    failure = classify_runtime_failure("provider outage")
    assert recovery_decision(failure, ack_active=True, github_writable=False) == "await-lease-expiry"


def test_review_refusal_never_changes_task_conclusion():
    failure = classify_runtime_failure("irrelevant refusal while reviewing benign orchestration")
    assert failure.substantive_task_failure is False
    assert recovery_decision(failure, ack_active=True, github_writable=True, phase="review") == "record-runtime-blocked-and-release"


def test_benign_security_misclassification_can_fail_over_to_compatible_runtime():
    failure = classify_runtime_failure("I refuse this benign orchestration request as security scanning")
    assert failure.kind is RuntimeFailureKind.PROVIDER_POLICY_REFUSAL
    assert failure.recoverable is True
    # Recovery is provider-neutral: the next compatible ChatGPT/Gemini-style dispatcher
    # may claim after release/expiry; no policy bypass is attempted.
    assert recovery_decision(failure, ack_active=True, github_writable=True) == "record-runtime-blocked-and-release"
