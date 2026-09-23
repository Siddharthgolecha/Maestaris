from __future__ import annotations

import unittest

from zerion_orchestration.capabilities import (
    capability_decision,
    list_field,
    select_capability_eligible,
    task_capabilities,
)


class CapabilityRoutingTests(unittest.TestCase):
    def test_legacy_task_remains_eligible_with_unknown_capabilities(self):
        decision = capability_decision("[ORCHESTRATOR:v1]\ntask_id: old\n", None)
        self.assertTrue(decision.eligible)

    def test_unknown_capabilities_do_not_satisfy_hard_requirement(self):
        decision = capability_decision("requires: [lean, github-write]\n", None)
        self.assertFalse(decision.eligible)
        self.assertEqual(decision.missing, ("github-write", "lean"))

    def test_missing_hard_capability_is_ineligible(self):
        body = """requires:
  - python
  - qiskit
prefers:
  - web
"""
        decision = capability_decision(body, ["python", "web"])
        self.assertFalse(decision.eligible)
        self.assertEqual(decision.missing, ("qiskit",))
        self.assertEqual(decision.preferred_matches, ("web",))

    def test_soft_preference_never_blocks_compatible_dispatcher(self):
        decision = capability_decision(
            "requires: github-write\nprefers: schedule-management\n",
            ["github-write"],
        )
        self.assertTrue(decision.eligible)
        self.assertEqual(decision.preference_misses, ("schedule-management",))

    def test_inline_and_block_lists_are_normalized(self):
        body = """requires: [Python, Web]
prefers:
  - Long-Reasoning
  - github-write
objective: |
  ignored
"""
        required, preferred = task_capabilities(body)
        self.assertEqual(required, frozenset({"python", "web"}))
        self.assertEqual(preferred, frozenset({"long-reasoning", "github-write"}))
        self.assertEqual(list_field("requires: []\n", "requires"), ())

    def test_dispatcher_selection_rejects_incompatible_before_preferences(self):
        tasks = [
            ("formal", "requires: [lean, github-write]\nprefers: [web]\n"),
            ("web", "requires: [web]\nprefers: [github-write]\n"),
            ("legacy", "task_id: legacy\n"),
        ]
        selected = select_capability_eligible(tasks, ["web"])
        self.assertEqual([task_id for task_id, _ in selected], ["web", "legacy"])
        self.assertEqual(selected[0][1].preferred_matches, ())
        self.assertTrue(all(decision.eligible for _, decision in selected))


if __name__ == "__main__":
    unittest.main()
