from __future__ import annotations

import unittest

from zerion_orchestration.audit import audit_snapshot, audit_task, duplicate_task_ids, reconcile_labels

CONFIG = {"task_label":"zerion:task","status_labels":{"ready":"zerion:ready","claimed":"zerion:claimed","blocked":"zerion:blocked","needs_review":"zerion:needs-review","accepted":"zerion:accepted","revise":"zerion:revise","rejected":"zerion:rejected"},"priority_label_prefix":"priority:"}
BODY = "[ORCHESTRATOR:v1]\ntask_id: t1\nproject: zerion\npriority: P0\ndepends_on:\n  []\nobjective: test\n"

class AuditTests(unittest.TestCase):
    def test_healthy_task_has_no_findings(self):
        self.assertEqual(audit_task(issue_body=BODY, comments=[], labels=["zerion:task","zerion:ready","priority:P0"], github_config=CONFIG), [])

    def test_label_drift_is_repairable_without_touching_unmanaged_labels(self):
        findings=audit_task(issue_body=BODY, comments=[], labels=["zerion:task","zerion:claimed","custom"], github_config=CONFIG)
        self.assertTrue(any(f.code=="derived-label-drift" and f.repairable for f in findings))
        self.assertEqual(reconcile_labels(BODY,[],["zerion:claimed","custom"],CONFIG),{"zerion:task","zerion:ready","priority:P0","custom"})

    def test_unreviewed_terminal_is_diagnostic_not_repairable(self):
        comments=["[WORKER:w:v1]\ntask_id: t1\nstatus: NEEDS_REVIEW\nsummary: done\n"]
        finding=next(f for f in audit_task(issue_body=BODY,comments=comments,labels=["zerion:task","zerion:needs-review","priority:P0"],github_config=CONFIG) if f.code=="unreviewed-terminal-result")
        self.assertFalse(finding.repairable)

    def test_accepted_open_mismatch_is_detected(self):
        comments=["[ORCHESTRATOR-REVIEW:v1]\ntask_id: t1\nstatus: ACCEPTED\n"]
        findings=audit_task(issue_body=BODY,comments=comments,labels=["zerion:task","zerion:accepted","priority:P0"],github_config=CONFIG)
        self.assertTrue(any(f.code=="accepted-open-mismatch" for f in findings))

    def test_duplicate_task_ids_are_reported(self):
        self.assertEqual(duplicate_task_ids([BODY,BODY,BODY.replace("t1","t2")]),{"t1"})

    def test_broken_dependency_is_nonrepairable(self):
        body=BODY.replace("depends_on:\n  []", "depends_on:\n  - missing-task")
        findings=audit_task(issue_body=body,comments=[],labels=["zerion:task","zerion:ready","priority:P0"],github_config=CONFIG,known_task_ids={"t1"})
        broken=next(f for f in findings if f.code=="broken-dependency")
        self.assertFalse(broken.repairable)

    def test_snapshot_detects_missing_reviewer_and_project_boundary(self):
        report=audit_snapshot({"tasks":[{"number":1,"body":BODY,"comments":[],"labels":["zerion:task","zerion:ready","priority:P0"]}]},CONFIG)
        codes={f["code"] for f in report["global_findings"]}
        self.assertIn("missing-recurring-reviewer",codes)
        self.assertIn("project-state-unavailable",codes)

    def test_healthy_snapshot_with_topology(self):
        report=audit_snapshot({"tasks":[{"number":1,"body":BODY,"comments":[],"labels":["zerion:task","zerion:ready","priority:P0"]}],"scheduler_topology":{"recurring_orchestrator":True},"project":{}},CONFIG)
        self.assertEqual(report["global_findings"],[])
        self.assertEqual(report["tasks"][0]["findings"],[])

    def test_contradictory_duplicate_snapshot(self):
        task={"body":BODY,"comments":[],"labels":["zerion:task","zerion:ready","priority:P0"]}
        report=audit_snapshot({"tasks":[dict(task,number=1),dict(task,number=2)],"scheduler_topology":{"recurring_orchestrator":True},"project":{}},CONFIG)
        self.assertTrue(all(any(f["code"]=="duplicate-task-id" for f in item["findings"]) for item in report["tasks"]))

if __name__ == "__main__": unittest.main()
