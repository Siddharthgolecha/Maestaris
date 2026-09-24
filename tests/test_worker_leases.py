from datetime import datetime, timezone
import unittest

from maestaris_orchestration.worker_leases import active_worker_lease, recovery_state, retry_count


def ack(worker="w1", dispatcher="d1", at="2026-09-23T10:00:00Z", hours="1", attempt="1", status="ACK"):
    return f"""[WORKER:{worker}:v1]
task_id: t1
status: {status}
dispatcher: {dispatcher}
claimed_at: {at}
lease_hours: {hours}
attempt: {attempt}
"""


class WorkerLeaseTests(unittest.TestCase):
    def test_crash_after_ack_expires_to_ready(self):
        comments = [ack()]
        self.assertEqual(recovery_state(comments, retry_budget=3, now=datetime(2026, 9, 23, 10, 30, tzinfo=timezone.utc)), "claimed")
        self.assertEqual(recovery_state(comments, retry_budget=3, now=datetime(2026, 9, 23, 11, 1, tzinfo=timezone.utc)), "ready")

    def test_crash_before_ack_consumes_no_retry(self):
        self.assertEqual(retry_count([]), 0)
        self.assertEqual(recovery_state([], retry_budget=3, now=datetime(2026, 9, 23, 10, tzinfo=timezone.utc)), "ready")

    def test_competing_ack_cannot_steal_active_lease(self):
        comments = [ack(), ack(worker="w2", dispatcher="d2", at="2026-09-23T10:10:00Z")]
        lease = active_worker_lease(comments, datetime(2026, 9, 23, 10, 30, tzinfo=timezone.utc))
        self.assertEqual((lease.worker, lease.dispatcher), ("w1", "d1"))
        self.assertEqual(retry_count(comments), 1)

    def test_owner_can_extend_but_not_shorten_or_rewind(self):
        comments = [
            ack(hours="2"),
            ack(at="2026-09-23T10:30:00Z", hours="3", status="RENEW"),
            ack(at="2026-09-23T10:15:00Z", hours="1", status="RENEW"),
        ]
        lease = active_worker_lease(comments, datetime(2026, 9, 23, 11, tzinfo=timezone.utc))
        self.assertEqual(lease.claimed_at.isoformat(), "2026-09-23T10:30:00+00:00")
        self.assertEqual(lease.expires_at.isoformat(), "2026-09-23T13:30:00+00:00")
        self.assertEqual(retry_count(comments), 1)

    def test_compatibility_ack_renewal_does_not_consume_retry(self):
        comments = [ack(hours="2"), ack(at="2026-09-23T10:30:00Z", hours="3")]
        self.assertEqual(retry_count(comments), 1)
        lease = active_worker_lease(comments, datetime(2026, 9, 23, 11, tzinfo=timezone.utc))
        self.assertEqual(lease.expires_at.isoformat(), "2026-09-23T13:30:00+00:00")

    def test_terminal_report_consumes_lease(self):
        terminal = """[WORKER:w1:v1]
task_id: t1
status: NEEDS_REVIEW
summary: complete
"""
        self.assertIsNone(active_worker_lease([ack(), terminal], datetime(2026, 9, 23, 10, 30, tzinfo=timezone.utc)))

    def test_future_and_malformed_claims_are_ignored(self):
        now = datetime(2026, 9, 23, 10, 30, tzinfo=timezone.utc)
        self.assertIsNone(active_worker_lease([ack(at="2026-09-23T12:00:00Z")], now))
        self.assertIsNone(active_worker_lease([ack(hours="nan")], now))

    def test_retry_budget_quarantines_without_erasing_history(self):
        comments = [
            ack(at="2026-09-23T08:00:00Z", attempt="1"),
            ack(worker="w2", dispatcher="d2", at="2026-09-23T10:00:00Z", attempt="2"),
        ]
        now = datetime(2026, 9, 23, 12, tzinfo=timezone.utc)
        self.assertEqual(retry_count(comments), 2)
        self.assertEqual(recovery_state(comments, retry_budget=2, now=now), "quarantine")
        self.assertEqual(recovery_state(comments, retry_budget=3, now=now), "ready")

    def test_duplicate_polling_does_not_inflate_retry_count(self):
        event = ack()
        self.assertEqual(retry_count([event, event]), 1)


if __name__ == "__main__":
    unittest.main()
