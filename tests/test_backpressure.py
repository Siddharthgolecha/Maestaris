import unittest

from zerion_orchestration.backpressure import dispatcher_admission, mistaken_ack_recovery


def worker(status, dispatcher="D", worker="w"):
    return f"[WORKER:{worker}:v1]\ntask_id: t\nstatus: {status}\ndispatcher: {dispatcher}\nsummary: x"


def review(status):
    return f"[ORCHESTRATOR-REVIEW:v1]\ntask_id: t\nstatus: {status}"


class DispatcherBackpressureTests(unittest.TestCase):
    def test_unreviewed_terminal_blocks_unrelated_ack(self):
        decision = dispatcher_admission({"A": [worker("NEEDS_REVIEW")]}, "D", 1)
        self.assertFalse(decision["allow_new"])
        self.assertEqual(decision["reason"], "pending-review-limit")
        self.assertEqual(decision["pending"], ("A",))

    def test_revise_routes_dispatcher_back_to_same_task(self):
        decision = dispatcher_admission({"A": [worker("NEEDS_REVIEW"), review("REVISE")]}, "D", 1)
        self.assertFalse(decision["allow_new"])
        self.assertEqual(decision["resume"], "A")
        self.assertEqual(decision["reason"], "resume-revise")

    def test_resumed_revise_remains_blocking_until_terminal(self):
        active = {"A": [worker("NEEDS_REVIEW"), review("REVISE"), worker("ACK")]}
        decision = dispatcher_admission(active, "D", 1)
        self.assertFalse(decision["allow_new"])
        self.assertEqual(decision["resume"], "A")
        self.assertEqual(decision["reason"], "resume-revise")

        terminal = {"A": [*active["A"], worker("NEEDS_REVIEW")]}
        decision = dispatcher_admission(terminal, "D", 1)
        self.assertFalse(decision["allow_new"])
        self.assertIsNone(decision["resume"])
        self.assertEqual(decision["reason"], "pending-review-limit")
        self.assertEqual(decision["pending"], ("A",))

    def test_accept_or_reject_releases_capacity(self):
        for status in ("ACCEPTED", "REJECTED"):
            with self.subTest(status=status):
                decision = dispatcher_admission({"A": [worker("NEEDS_REVIEW"), review(status)]}, "D", 1)
                self.assertTrue(decision["allow_new"])

    def test_multiple_worker_identities_share_dispatcher_capacity(self):
        histories = {"A": [worker("DONE", worker="one")], "B": [worker("ACK", worker="two")]}
        decision = dispatcher_admission(histories, "D", 1)
        self.assertFalse(decision["allow_new"])
        self.assertEqual(decision["pending"], ("A",))

    def test_other_dispatcher_does_not_consume_capacity(self):
        decision = dispatcher_admission({"A": [worker("NEEDS_REVIEW", dispatcher="other")]}, "D", 1)
        self.assertTrue(decision["allow_new"])

    def test_live_gemini_style_violation_is_rejected(self):
        # #37 terminal result from one dispatcher followed by an unrelated #40 ACK
        # is precisely the scheduling decision the admission gate prevents.
        histories_before_bad_ack = {"37": [worker("NEEDS_REVIEW", dispatcher="gemini-spark-b2")]}
        decision = dispatcher_admission(histories_before_bad_ack, "gemini-spark-b2", 1)
        self.assertFalse(decision["allow_new"])
        self.assertEqual(decision["reason"], "pending-review-limit")

    def test_mistaken_ack_is_preserved_not_rewritten(self):
        comments = [worker("ACK")]
        self.assertEqual(mistaken_ack_recovery(comments, "D"), "stop-without-rewrite")
        self.assertEqual(len(comments), 1)


if __name__ == "__main__":
    unittest.main()
