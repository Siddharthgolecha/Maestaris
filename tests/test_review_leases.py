from __future__ import annotations

from datetime import datetime, timezone
import unittest

from maestaris_orchestration.protocol import (
    active_review_claim,
    reduce_task_status,
    review_claim_available,
    validate_protocol_comment,
)


class ReviewLeaseTests(unittest.TestCase):
    def setUp(self):
        self.claim = """[ORCHESTRATOR-CLAIM:v1]
task_id: t1
orchestrator: chatgpt-orchestrator
runtime: chatgpt
instance: maestaris-chatgpt-orchestrator
claimed_at: 2026-09-23T04:00:00Z
lease_hours: 1
"""

    def test_claim_validates_and_does_not_change_task_status(self):
        self.assertEqual(validate_protocol_comment(self.claim), [])
        self.assertEqual(reduce_task_status([self.claim]), "ready")

    def test_active_claim_blocks_other_orchestrator_but_allows_renewal(self):
        now = datetime(2026, 9, 23, 4, 30, tzinfo=timezone.utc)
        self.assertEqual(active_review_claim([self.claim], now)["orchestrator"], "chatgpt-orchestrator")
        self.assertTrue(review_claim_available([self.claim], "chatgpt-orchestrator", now))
        self.assertFalse(review_claim_available([self.claim], "gemini-orchestrator", now))

    def test_expired_claim_is_recoverable(self):
        now = datetime(2026, 9, 23, 5, 30, tzinfo=timezone.utc)
        self.assertIsNone(active_review_claim([self.claim], now))
        self.assertTrue(review_claim_available([self.claim], "gemini-orchestrator", now))

    def test_terminal_review_consumes_claim(self):
        review = """[ORCHESTRATOR-REVIEW:v1]
task_id: t1
status: ACCEPTED
"""
        now = datetime(2026, 9, 23, 4, 30, tzinfo=timezone.utc)
        self.assertIsNone(active_review_claim([self.claim, review], now))
        self.assertEqual(reduce_task_status([self.claim, review]), "accepted")

    def test_invalid_claim_is_rejected(self):
        errors = validate_protocol_comment("[ORCHESTRATOR-CLAIM:v1]\ntask_id: t1\norchestrator: gemini\n")
        self.assertTrue(any("claimed_at" in error for error in errors))
        self.assertTrue(any("lease_hours" in error for error in errors))

    def test_malformed_timestamp_and_durations_are_rejected(self):
        bad_time = """[ORCHESTRATOR-CLAIM:v1]
task_id: t1
orchestrator: chatgpt-orchestrator
claimed_at: invalid-timestamp
lease_hours: 1
"""
        self.assertTrue(any("claimed_at" in e for e in validate_protocol_comment(bad_time)))
        for bad_hours in ("nan", "inf", "-1", "0", "abc"):
            claim = f"""[ORCHESTRATOR-CLAIM:v1]
task_id: t1
orchestrator: chatgpt-orchestrator
claimed_at: 2026-09-23T04:00:00Z
lease_hours: {bad_hours}
"""
            errors = validate_protocol_comment(claim)
            self.assertTrue(any("lease_hours" in e for e in errors), f"Failed for lease_hours: {bad_hours}")

    def test_valid_active_claim_remains_authoritative_when_followed_by_malformed_claim(self):
        malformed_claim = """[ORCHESTRATOR-CLAIM:v1]
task_id: t1
orchestrator: rogue-orchestrator
claimed_at: 2026-09-23T04:15:00Z
lease_hours: nan
"""
        now = datetime(2026, 9, 23, 4, 30, tzinfo=timezone.utc)
        claim = active_review_claim([self.claim, malformed_claim], now)
        self.assertIsNotNone(claim)
        self.assertEqual(claim["orchestrator"], "chatgpt-orchestrator")

    def test_competing_claim_cannot_steal_unexpired_lease(self):
        competing_claim = """[ORCHESTRATOR-CLAIM:v1]
task_id: t1
orchestrator: gemini-orchestrator
claimed_at: 2026-09-23T04:15:00Z
lease_hours: 1
"""
        now = datetime(2026, 9, 23, 4, 30, tzinfo=timezone.utc)
        claim = active_review_claim([self.claim, competing_claim], now)
        self.assertIsNotNone(claim)
        self.assertEqual(claim["orchestrator"], "chatgpt-orchestrator")

    def test_future_competing_claim_cannot_displace_current_lease_early(self):
        current = """[ORCHESTRATOR-CLAIM:v1]
task_id: t1
orchestrator: chatgpt-orchestrator
claimed_at: 2026-09-23T04:00:00Z
lease_hours: 2
"""
        future = """[ORCHESTRATOR-CLAIM:v1]
task_id: t1
orchestrator: gemini-orchestrator
claimed_at: 2026-09-23T07:00:00Z
lease_hours: 1
"""
        now = datetime(2026, 9, 23, 4, 30, tzinfo=timezone.utc)
        claim = active_review_claim([current, future], now)
        self.assertIsNotNone(claim)
        self.assertEqual(claim["orchestrator"], "chatgpt-orchestrator")

    def test_lone_future_claim_is_not_active_before_start(self):
        future = """[ORCHESTRATOR-CLAIM:v1]
task_id: t1
orchestrator: gemini-orchestrator
claimed_at: 2026-09-23T07:00:00Z
lease_hours: 1
"""
        now = datetime(2026, 9, 23, 4, 30, tzinfo=timezone.utc)
        self.assertIsNone(active_review_claim([future], now))

    def test_stale_same_owner_renewal_cannot_rewind_newer_lease(self):
        renewal = """[ORCHESTRATOR-CLAIM:v1]
task_id: t1
orchestrator: chatgpt-orchestrator
claimed_at: 2026-09-23T04:30:00Z
lease_hours: 2
"""
        stale = """[ORCHESTRATOR-CLAIM:v1]
task_id: t1
orchestrator: chatgpt-orchestrator
claimed_at: 2026-09-23T04:10:00Z
lease_hours: 1
"""
        now = datetime(2026, 9, 23, 5, 15, tzinfo=timezone.utc)
        claim = active_review_claim([self.claim, renewal, stale], now)
        self.assertIsNotNone(claim)
        self.assertEqual(claim["claimed_at"], "2026-09-23T04:30:00Z")

    def test_shorter_same_owner_renewal_cannot_shorten_active_lease(self):
        long_claim = """[ORCHESTRATOR-CLAIM:v1]
task_id: t1
orchestrator: chatgpt-orchestrator
claimed_at: 2026-09-23T04:00:00Z
lease_hours: 3
"""
        shorter = """[ORCHESTRATOR-CLAIM:v1]
task_id: t1
orchestrator: chatgpt-orchestrator
claimed_at: 2026-09-23T05:00:00Z
lease_hours: 1
"""
        now = datetime(2026, 9, 23, 5, 30, tzinfo=timezone.utc)
        claim = active_review_claim([long_claim, shorter], now)
        self.assertIsNotNone(claim)
        self.assertEqual(claim["claimed_at"], "2026-09-23T04:00:00Z")


if __name__ == "__main__":
    unittest.main()
