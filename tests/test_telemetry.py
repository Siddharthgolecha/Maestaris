from datetime import datetime, timezone
import unittest

from maestaris_orchestration.protocol import reduce_task_status
from maestaris_orchestration.telemetry import export_payload, lifecycle_metrics, project_lifecycle_events


ACK = """[WORKER:worker-a:v1]
task_id: telemetry
status: ACK
dispatcher: pool-a
runtime: chatgpt
claimed_at: 2026-09-25T10:00:00Z
lease_hours: 1
"""
CHECKPOINT = """[WORKER:worker-a:v1]
task_id: telemetry
status: CHECKPOINT
dispatcher: pool-a
runtime: chatgpt
claimed_at: 2026-09-25T10:20:00Z
"""
NEEDS_REVIEW = """[WORKER:worker-a:v1]
task_id: telemetry
status: NEEDS_REVIEW
dispatcher: pool-a
runtime: chatgpt
claimed_at: 2026-09-25T11:00:00Z
"""
ACCEPT = """[ORCHESTRATOR-REVIEW:v1]
task_id: telemetry
status: ACCEPTED
claimed_at: 2026-09-25T11:15:00Z
"""


class LifecycleTelemetryTests(unittest.TestCase):
    def setUp(self):
        self.comments = [
            {"body": ACK, "created_at": "2026-09-25T10:00:00Z"},
            {"body": CHECKPOINT, "created_at": "2026-09-25T10:20:00Z"},
            {"body": NEEDS_REVIEW, "created_at": "2026-09-25T11:00:00Z"},
            {"body": ACCEPT, "created_at": "2026-09-25T11:15:00Z"},
        ]

    def test_projection_is_machine_readable_and_rebuildable(self):
        events = project_lifecycle_events(self.comments, trace_id="advisory-trace")
        self.assertEqual([e.status for e in events], ["ACK", "CHECKPOINT", "NEEDS_REVIEW", "ACCEPTED"])
        self.assertTrue(all(e.trace_id == "advisory-trace" for e in events))
        metrics = lifecycle_metrics(
            self.comments,
            issue_created_at="2026-09-25T09:55:00Z",
            now=datetime(2026, 9, 25, 11, 20, tzinfo=timezone.utc),
        )
        self.assertEqual(metrics["queue_latency_seconds"], 300)
        self.assertEqual(metrics["cycle_latency_seconds"], 3600)
        self.assertEqual(metrics["review_latency_seconds"], 900)
        self.assertEqual(metrics["checkpoints"], 1)
        self.assertEqual(metrics["activity"]["chatgpt/pool-a"], 3)

    def test_projection_cannot_change_canonical_task_state(self):
        bodies = [item["body"] for item in self.comments]
        before = reduce_task_status(bodies)
        snapshot = [dict(item) for item in self.comments]
        payload = export_payload(self.comments, issue_created_at="2026-09-25T09:55:00Z", trace_id="not-authority")
        after = reduce_task_status(bodies)
        self.assertEqual(before, after)
        self.assertEqual(self.comments, snapshot)
        self.assertEqual(payload["metrics"]["canonical_status"], before)
        self.assertEqual(payload["trace_id"], "not-authority")

    def test_export_is_credential_free_and_trace_id_is_advisory(self):
        payload = export_payload(self.comments, trace_id="correlation-only")
        rendered = repr(payload).lower()
        for forbidden in ("authorization", "password", "secret", "token"):
            self.assertNotIn(forbidden, rendered)
        self.assertEqual(payload["trace_id"], "correlation-only")
        self.assertEqual(payload["events"][0]["task_id"], "telemetry")


if __name__ == "__main__":
    unittest.main()
