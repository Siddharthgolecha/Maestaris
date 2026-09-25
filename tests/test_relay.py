import json
import unittest

from maestaris_orchestration.relay import (
    comment_has_event_id,
    parse_relay_request,
    validate_relay_request,
)


ACK = """[WORKER:worker-a:v1]
task_id: task-1
status: ACK
dispatcher: pool-a
claimed_at: 2026-09-25T03:00:00Z
lease_hours: 3
relay_event_id: task-1.pool-a.ack.20260925T030000Z
"""


class RelayTests(unittest.TestCase):
    def test_valid_worker_ack_request(self):
        payload = {
            "schema": 1,
            "event_id": "task-1.pool-a.ack.20260925T030000Z",
            "issue_number": 12,
            "body": ACK,
        }
        self.assertEqual(validate_relay_request(payload), [])
        self.assertEqual(parse_relay_request(json.dumps(payload)), payload)

    def test_event_id_must_match_body(self):
        payload = {
            "schema": 1,
            "event_id": "different",
            "issue_number": 12,
            "body": ACK,
        }
        self.assertIn("relay body relay_event_id must equal event_id", validate_relay_request(payload))

    def test_arbitrary_comment_is_rejected(self):
        payload = {
            "schema": 1,
            "event_id": "x",
            "issue_number": 12,
            "body": "hello\nrelay_event_id: x\n",
        }
        errors = validate_relay_request(payload)
        self.assertTrue(any("canonical Maestaris" in error for error in errors))

    def test_invalid_protocol_event_is_rejected(self):
        payload = {
            "schema": 1,
            "event_id": "bad",
            "issue_number": 12,
            "body": """[WORKER:w:v1]
task_id: t
status: ACK
relay_event_id: bad
""",
        }
        errors = validate_relay_request(payload)
        self.assertTrue(any("ACK is missing dispatcher" in error for error in errors))

    def test_comment_event_id_is_exact_protocol_field(self):
        self.assertTrue(comment_has_event_id(ACK, "task-1.pool-a.ack.20260925T030000Z"))
        self.assertFalse(comment_has_event_id(ACK, "task-1"))


if __name__ == "__main__":
    unittest.main()
