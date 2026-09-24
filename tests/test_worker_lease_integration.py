from datetime import datetime, timezone
import unittest

from maestaris_orchestration.audit import audit_task
from maestaris_orchestration.protocol import reduce_task_status, validate_protocol_comment

CONFIG = {
    "task_label": "maestaris:task",
    "status_labels": {
        "ready": "maestaris:ready",
        "claimed": "maestaris:claimed",
        "blocked": "maestaris:blocked",
        "needs_review": "maestaris:needs-review",
        "accepted": "maestaris:accepted",
        "revise": "maestaris:revise",
        "rejected": "maestaris:rejected",
    },
    "priority_label_prefix": "priority:",
    "worker_retry_budget": 2,
}
BODY = "[ORCHESTRATOR:v1]\ntask_id: t1\nproject: maestaris\npriority: P0\ndepends_on:\n  []\nobjective: test\n"


def event(status="ACK", at="2026-09-23T10:00:00Z", worker="w1", dispatcher="d1"):
    return f"""[WORKER:{worker}:v1]
task_id: t1
status: {status}
dispatcher: {dispatcher}
claimed_at: {at}
lease_hours: 1
attempt: 1
"""


class WorkerLeaseIntegrationTests(unittest.TestCase):
    def test_renew_is_first_class_protocol_event_and_preserves_claimed_status(self):
        renew = event("RENEW", "2026-09-23T10:30:00Z")
        self.assertEqual(validate_protocol_comment(renew), [])
        self.assertEqual(reduce_task_status([event(), renew]), "claimed")

    def test_renew_rejects_malformed_lease_metadata(self):
        bad = event("RENEW").replace("lease_hours: 1", "lease_hours: nan")
        self.assertTrue(any("lease_hours" in error for error in validate_protocol_comment(bad)))

    def test_audit_marks_expired_lease_recoverable_without_rewriting_history(self):
        comments = [event()]
        findings = audit_task(
            issue_body=BODY,
            comments=comments,
            labels=["maestaris:task", "maestaris:claimed", "priority:P0"],
            github_config=CONFIG,
            now=datetime(2026, 9, 23, 11, 1, tzinfo=timezone.utc),
        )
        finding = next(f for f in findings if f.code == "expired-worker-lease")
        self.assertFalse(finding.repairable)
        self.assertEqual(comments, [event()])

    def test_audit_quarantines_after_retry_budget_without_history_mutation(self):
        comments = [
            event(at="2026-09-23T08:00:00Z"),
            event(at="2026-09-23T10:00:00Z", worker="w2", dispatcher="d2"),
        ]
        original = list(comments)
        findings = audit_task(
            issue_body=BODY,
            comments=comments,
            labels=["maestaris:task", "maestaris:claimed", "priority:P0"],
            github_config=CONFIG,
            now=datetime(2026, 9, 23, 12, tzinfo=timezone.utc),
        )
        finding = next(f for f in findings if f.code == "worker-retry-quarantine")
        self.assertFalse(finding.repairable)
        self.assertEqual(comments, original)


if __name__ == "__main__":
    unittest.main()
