from datetime import datetime, timezone
import unittest

from maestaris_orchestration.backpressure import dispatcher_admission
from maestaris_orchestration.simulation import conformance_report, invariant_violations

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=timezone.utc)


def ack(dispatcher, at="2026-09-24T11:00:00Z", hours=3):
    return f"""[WORKER:w:v1]\nstatus: ACK\ndispatcher: {dispatcher}\nclaimed_at: {at}\nlease_hours: {hours}"""


def terminal(dispatcher, status="NEEDS_REVIEW"):
    return f"""[WORKER:w:v1]\nstatus: {status}\ndispatcher: {dispatcher}"""


def review(status):
    return f"""[ORCHESTRATOR-REVIEW:v1]\nstatus: {status}"""


def claim(owner, at="2026-09-24T11:00:00Z", hours=3):
    return f"""[ORCHESTRATOR-CLAIM:v1]\norchestrator: {owner}\nclaimed_at: {at}\nlease_hours: {hours}"""


class SimulationInvariantTests(unittest.TestCase):
    def test_compliant_transcript_passes(self):
        histories = {"a": [ack("d"), terminal("d"), claim("o"), review("ACCEPTED")]}
        self.assertTrue(conformance_report(histories, now=NOW)["passed"])

    def test_worker_ack_race_is_detected(self):
        violations = invariant_violations({"a": [ack("d1"), ack("d2")]}, now=NOW)
        self.assertEqual([v.invariant for v in violations], ["single-worker-owner"])

    def test_expired_worker_lease_recovers(self):
        old = ack("dead", at="2026-09-24T07:00:00Z", hours=1)
        self.assertFalse(invariant_violations({"a": [old, ack("recovery")]}, now=NOW))

    def test_crash_then_retry_after_expiry_recovers_safely(self):
        crashed = ack("worker-before-crash", at="2026-09-24T06:00:00Z", hours=1)
        retry = ack("worker-after-restart")
        report = conformance_report({"a": [crashed, retry]}, now=NOW)
        self.assertTrue(report["passed"])

    def test_retry_before_expiry_is_rejected_as_competing_owner(self):
        violations = invariant_violations({"a": [ack("live"), ack("retry")]}, now=NOW)
        self.assertEqual([v.invariant for v in violations], ["single-worker-owner"])

    def test_duplicate_delivery_same_owner_is_idempotent(self):
        self.assertFalse(invariant_violations({"a": [ack("d"), ack("d")]}, now=NOW))

    def test_review_race_is_detected_and_expiry_recovers(self):
        race = {"a": [terminal("d"), claim("o1"), claim("o2")]}
        self.assertIn("single-review-owner", [v.invariant for v in invariant_violations(race, now=NOW)])
        expired = claim("old", at="2026-09-24T07:00:00Z", hours=1)
        self.assertFalse(invariant_violations({"a": [terminal("d"), expired, claim("new")]}, now=NOW))

    def test_orchestrator_crash_then_review_lease_recovery(self):
        crashed = claim("dead-reviewer", at="2026-09-24T07:00:00Z", hours=1)
        self.assertFalse(invariant_violations({"a": [terminal("d"), crashed, claim("recovery-reviewer")]}, now=NOW))

    def test_acceptance_without_terminal_evidence_fails(self):
        violations = invariant_violations({"a": [claim("o"), review("ACCEPTED")]}, now=NOW)
        self.assertEqual(violations[0].invariant, "acceptance-requires-terminal-evidence")

    def test_late_ci_cannot_be_accepted_before_terminal_report(self):
        # CI/dashboard chatter is advisory; only a durable worker terminal event unlocks acceptance.
        late_ci = "[DERIVED-CI]\nconclusion: success\nhead: abc123"
        violations = invariant_violations({"a": [ack("d"), late_ci, review("ACCEPTED")]}, now=NOW)
        self.assertEqual([v.invariant for v in violations], ["acceptance-requires-terminal-evidence"])

    def test_merge_before_report_cannot_manufacture_acceptance_evidence(self):
        merged = "[DERIVED-PR]\nstate: merged\nhead: abc123"
        violations = invariant_violations({"a": [ack("d"), merged, review("ACCEPTED")]}, now=NOW)
        self.assertEqual([v.invariant for v in violations], ["acceptance-requires-terminal-evidence"])

    def test_stale_branch_metadata_cannot_override_issue_history(self):
        stale = "[DERIVED-PR]\nmergeable: false\nbehind_by: 4"
        self.assertFalse(invariant_violations({"a": [ack("d"), stale]}, now=NOW))

    def test_derived_project_and_label_state_is_non_authoritative(self):
        derived = [
            "[DERIVED-LABEL]\nstatus: ACCEPTED",
            "[DERIVED-PROJECT]\nstatus: Done\nworker: somebody-else",
        ]
        # Derived views cannot erase the live canonical ACK or create an acceptance.
        self.assertFalse(invariant_violations({"a": [ack("canonical-owner"), *derived]}, now=NOW))
        report = conformance_report({"a": [ack("canonical-owner"), *derived]}, now=NOW)
        self.assertEqual(report["canonical_source"], "github-issue-history")

    def test_provider_outage_is_dormant_and_recovery_can_claim_later(self):
        # No provider event means no invented owner; a later provider may safely claim.
        self.assertFalse(invariant_violations({"a": []}, now=NOW))
        self.assertFalse(invariant_violations({"a": [ack("provider-after-outage")]}, now=NOW))

    def test_dependency_wait_does_not_create_canonical_ownership(self):
        waiting = "[SCHEDULER]\nstatus: WAITING\ndepends_on: upstream"
        self.assertFalse(invariant_violations({"a": [waiting]}, now=NOW))
        # Once dependency resolution is durably reflected by normal dispatch, ownership is ordinary ACK state.
        self.assertFalse(invariant_violations({"a": [waiting, ack("d")]}, now=NOW))

    def test_live_gemini_backpressure_interleaving_fails_admission(self):
        # Regression fixture for the observed #37 -> #40 scheduling violation.
        histories = {"37": [ack("gemini-spark-b2"), terminal("gemini-spark-b2")]}
        decision = dispatcher_admission(histories, "gemini-spark-b2", 1)
        self.assertFalse(decision["allow_new"])
        self.assertEqual(decision["reason"], "pending-review-limit")

    def test_revise_forces_same_dispatcher_resumption(self):
        histories = {"37": [ack("d"), terminal("d"), review("REVISE")]}
        decision = dispatcher_admission(histories, "d", 2)
        self.assertFalse(decision["allow_new"])
        self.assertEqual(decision["resume"], "37")

    def test_negative_terminal_evidence_remains_valid_evidence(self):
        for status in ("BLOCKED", "DONE", "NEEDS_REVIEW"):
            with self.subTest(status=status):
                report = conformance_report({"a": [ack("d"), terminal("d", status), review("ACCEPTED")]}, now=NOW)
                self.assertTrue(report["passed"])

    def test_negative_evidence_is_not_erased_by_later_derived_success(self):
        history = [ack("d"), terminal("d", "BLOCKED"), "[DERIVED-CI]\nconclusion: success", review("ACCEPTED")]
        self.assertTrue(conformance_report({"a": history}, now=NOW)["passed"])

    def test_projection_is_deterministic(self):
        histories = {"a": [ack("d1"), ack("d2")]}
        self.assertEqual(conformance_report(histories, now=NOW), conformance_report(histories, now=NOW))


if __name__ == "__main__":
    unittest.main()
