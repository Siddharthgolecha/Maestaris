from __future__ import annotations

import unittest

from zerion_orchestration.capabilities import capability_decision, list_field, task_capabilities


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


if __name__ == "__main__":
    unittest.main()
