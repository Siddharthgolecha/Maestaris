import unittest

from maestaris_orchestration.conformance import (
    ALL_INVARIANTS,
    compliant_recorded_scenario,
    evaluate,
    gemini_backpressure_violation_scenario,
    observations_from_mapping,
    runtime_failure_scenario,
)


class ConformanceTests(unittest.TestCase):
    def test_compliant_transcript_passes_every_invariant(self):
        result = evaluate("recorded-compliant", compliant_recorded_scenario())
        self.assertTrue(result.compliant)
        self.assertEqual(result.failed, ())
        self.assertEqual(set(result.passed), set(ALL_INVARIANTS))
        self.assertIs(result.as_dict()["advisory"], True)

    def test_live_gemini_backpressure_regression_fails(self):
        result = evaluate("gemini-spark", gemini_backpressure_violation_scenario())
        self.assertFalse(result.compliant)
        self.assertEqual(result.failed, ("review-backpressure",))

    def test_runtime_failures_require_compatible_recovery(self):
        for kind in (
            "provider-policy-refusal",
            "tool-auth-denied",
            "provider-outage",
            "malformed-or-irrelevant-refusal",
        ):
            with self.subTest(kind=kind):
                passed = evaluate(
                    "recorded",
                    runtime_failure_scenario(kind, recovered_by_compatible_runtime=True),
                    require_all=False,
                )
                failed = evaluate(
                    "recorded",
                    runtime_failure_scenario(kind, recovered_by_compatible_runtime=False),
                    require_all=False,
                )
                self.assertTrue(passed.compliant)
                self.assertFalse(failed.compliant)

    def test_missing_required_invariants_fail_closed(self):
        result = evaluate(
            "partial",
            observations_from_mapping(
                [{"invariant": "ack-arbitration", "passed": True, "evidence": "first ACK won"}]
            ),
        )
        self.assertFalse(result.compliant)
        self.assertIn("dependencies", result.failed)

    def test_unknown_invariant_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown invariant"):
            evaluate(
                "bad",
                observations_from_mapping(
                    [{"invariant": "provider-says-ok", "passed": True}]
                ),
            )


if __name__ == "__main__":
    unittest.main()
