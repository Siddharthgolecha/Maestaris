import unittest

from maestaris_orchestration.execution_routing import (
    RoutePlan,
    System1Signal,
    TaskFeatures,
    apply_system1_signal,
    bounded_tool_plan,
    deterministic_route,
    executor_envelope,
    verifier_escalation,
)


class ExecutionRoutingTests(unittest.TestCase):
    def test_baseline_is_deterministic(self):
        features = TaskFeatures(
            task_id="t",
            requires_write=True,
            requires_code_generation=True,
            context_chars=1000,
        )
        self.assertEqual(deterministic_route(features), deterministic_route(features))
        self.assertEqual(deterministic_route(features).selected_tier, "standard")

    def test_formal_or_high_risk_floor_is_frontier(self):
        for features in (
            TaskFeatures(task_id="formal", requires_formal_proof=True),
            TaskFeatures(task_id="risk", high_risk=True),
        ):
            with self.subTest(features=features.task_id):
                plan = deterministic_route(features)
                self.assertEqual(plan.minimum_tier, "frontier")
                lowered = apply_system1_signal(
                    plan,
                    System1Signal("small", 0.999, source="laya"),
                )
                self.assertEqual(lowered.selected_tier, "frontier")
                self.assertIn("floor-rejected", lowered.decision_source)

    def test_uncertain_downgrade_keeps_baseline(self):
        features = TaskFeatures(
            task_id="long",
            requires_write=True,
            context_chars=25000,
        )
        baseline = deterministic_route(features, long_context_chars=20000)
        self.assertEqual(baseline.selected_tier, "frontier")
        result = apply_system1_signal(
            baseline,
            System1Signal("standard", 0.80, source="jev"),
            downgrade_confidence=0.90,
        )
        self.assertEqual(result.selected_tier, "frontier")
        self.assertIn("uncertain-downgrade", result.decision_source)

    def test_confident_downgrade_may_reach_but_not_cross_floor(self):
        baseline = deterministic_route(
            TaskFeatures(task_id="long", requires_write=True, context_chars=25000),
            long_context_chars=20000,
        )
        result = apply_system1_signal(
            baseline,
            System1Signal("standard", 0.97, source="laya"),
            downgrade_confidence=0.90,
        )
        self.assertEqual(result.minimum_tier, "standard")
        self.assertEqual(result.selected_tier, "standard")

    def test_verifier_failure_escalates_one_lane(self):
        plan = RoutePlan("t", "small", "small", "deterministic", None, ())
        failed = verifier_escalation(plan, "failed")
        self.assertEqual(failed.selected_tier, "standard")
        self.assertIn("verifier", failed.decision_source)
        self.assertEqual(verifier_escalation(failed, "passed"), failed)

    def test_typed_answers_parse_like_laya_or_jev(self):
        signal = System1Signal.from_typed_answers(
            {
                "route": {"type": "choice", "choice": "standard", "confidence": 0.91},
                "needs_reasoning": {"type": "noul", "noul": 0.82},
                "complexity": {"type": "score", "score": 2.7, "confidence": 0.8},
            },
            source="laya",
        )
        self.assertEqual(signal.recommended_tier, "standard")
        self.assertAlmostEqual(signal.confidence, 0.91)
        self.assertAlmostEqual(signal.needs_reasoning_probability, 0.82)

    def test_needle3_tools_are_confidence_and_allowlist_gated(self):
        response = {
            "confidence": 0.94,
            "function_calls": [
                {"name": "read_issue", "arguments": {"issue_number": 46}},
                {"name": "run_verifier", "arguments": {}},
            ],
        }
        accepted = bounded_tool_plan(
            response,
            allowlisted_tools=("read_issue", "run_verifier"),
            minimum_confidence=0.70,
        )
        self.assertTrue(accepted.accepted)
        denied = bounded_tool_plan(
            {"confidence": 0.99, "function_calls": [{"name": "delete_repo", "arguments": {}}]},
            allowlisted_tools=("read_issue",),
        )
        self.assertFalse(denied.accepted)
        self.assertIn("not allowlisted", denied.reason)

    def test_executor_envelope_contains_authority_boundary_not_secrets(self):
        plan = deterministic_route(TaskFeatures(task_id="t", requires_write=True))
        envelope = executor_envelope(
            repository="owner/repo",
            issue_number=12,
            branch="maestaris/task/12",
            pr_number=13,
            expected_head_sha="abc",
            plan=plan,
            allowed_tools=("read_issue", "update_task_branch"),
        )
        self.assertEqual(envelope["task_id"], "t")
        self.assertEqual(envelope["issue_number"], 12)
        self.assertEqual(envelope["allowed_tools"], ["read_issue", "update_task_branch"])
        self.assertNotIn("token", envelope)
        self.assertNotIn("api_key", envelope)


if __name__ == "__main__":
    unittest.main()
