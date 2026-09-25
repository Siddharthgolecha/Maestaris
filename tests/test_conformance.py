import pytest

from maestaris_orchestration.conformance import (
    ALL_INVARIANTS, compliant_recorded_scenario, evaluate,
    gemini_backpressure_violation_scenario, observations_from_mapping,
    runtime_failure_scenario,
)

def test_compliant_transcript_passes_every_invariant():
    result = evaluate("recorded-compliant", compliant_recorded_scenario())
    assert result.compliant
    assert result.failed == ()
    assert set(result.passed) == set(ALL_INVARIANTS)
    assert result.as_dict()["advisory"] is True

def test_live_gemini_backpressure_regression_fails():
    result = evaluate("gemini-spark", gemini_backpressure_violation_scenario())
    assert not result.compliant
    assert result.failed == ("review-backpressure",)

@pytest.mark.parametrize("kind", [
    "provider-policy-refusal", "tool-auth-denied", "provider-outage",
    "malformed-or-irrelevant-refusal",
])
def test_runtime_failures_require_compatible_recovery(kind):
    passed = evaluate("recorded", runtime_failure_scenario(kind, recovered_by_compatible_runtime=True), require_all=False)
    failed = evaluate("recorded", runtime_failure_scenario(kind, recovered_by_compatible_runtime=False), require_all=False)
    assert passed.compliant
    assert not failed.compliant

def test_missing_required_invariants_fail_closed():
    result = evaluate("partial", observations_from_mapping([
        {"invariant": "ack-arbitration", "passed": True, "evidence": "first ACK won"}
    ]))
    assert not result.compliant
    assert "dependencies" in result.failed

def test_unknown_invariant_is_rejected():
    with pytest.raises(ValueError, match="unknown invariant"):
        evaluate("bad", observations_from_mapping([{"invariant": "provider-says-ok", "passed": True}]))
