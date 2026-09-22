from __future__ import annotations

import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import yaml

from zerion_orchestration.cli import main
from zerion_orchestration.core import validate_repository
from zerion_orchestration.protocol import (
    desired_managed_labels,
    is_managed_label,
    pinned_worker,
    reduce_task_status,
    validate_protocol_comment,
    validate_task_issue,
    worker_from_event,
)


class ZerionProtocolV4Tests(unittest.TestCase):
    def init_project(self, root: Path) -> int:
        return main(
            [
                "--root", str(root),
                "init", "alpha",
                "--workers", "theory", "build", "audit",
                "--repository", "example/alpha",
            ]
        )

    def test_init_is_static_and_github_native(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = self.init_project(root)
            self.assertEqual(code, 0)

            registry = yaml.safe_load(
                (root / "coordination" / "zerion.yaml").read_text()
            )
            project = yaml.safe_load(
                (root / "coordination" / "projects" / "alpha.yaml").read_text()
            )

            self.assertEqual(registry["protocol_version"], 4)
            self.assertEqual(registry["github"]["task_transport"], "issue")
            self.assertEqual(registry["github"]["task_label"], "zerion:task")
            self.assertEqual(
                registry["github"]["status_labels"]["ready"],
                "zerion:ready",
            )
            self.assertNotIn("assigned", registry["github"]["status_labels"])

            self.assertEqual(
                project["active_workers"],
                ["alpha-theory", "alpha-build", "alpha-audit"],
            )
            self.assertEqual(project["control_plane"]["transport"], "github_issue")
            self.assertNotIn("mailboxes", project)

            for worker in project["active_workers"]:
                agent = yaml.safe_load(
                    (root / "coordination" / "agents" / f"{worker}.yaml").read_text()
                )
                self.assertEqual(agent["control_plane"]["transport"], "github_issue")
                self.assertNotIn("mailbox", agent)
                self.assertNotIn("current_task", agent)
                self.assertNotIn("current_objective", agent)

            self.assertFalse((root / "coordination" / "state").exists())
            self.assertFalse((root / "coordination" / "mailboxes").exists())
            self.assertEqual(main(["--root", str(root), "validate"]), 0)

    def test_existing_agents_md_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "AGENTS.md"
            path.write_text("# Existing\nDo not overwrite.\n")
            self.assertEqual(self.init_project(root), 0)
            self.assertEqual(path.read_text(), "# Existing\nDo not overwrite.\n")

    def test_duplicate_project_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(self.init_project(root), 0)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(self.init_project(root), 2)

    def test_invalid_name_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(
                    main(
                        [
                            "--root", tmp,
                            "init", "Bad Name",
                            "--workers", "theory",
                            "--repository", "example/alpha",
                        ]
                    ),
                    2,
                )

    def test_protocol_v4_rejects_shadow_state_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(self.init_project(root), 0)
            state = root / "coordination" / "state"
            state.mkdir()
            (state / "alpha-theory.yaml").write_text("worker: alpha-theory\n")

            result = validate_repository(root)
            self.assertFalse(result.ok)
            self.assertTrue(
                any("removed mutable state/mailbox files" in e for e in result.errors)
            )

    def test_new_task_is_ready_without_worker_or_status(self):
        body = """[ORCHESTRATOR:v1]
task_id: alpha-proof-0001
project: alpha
priority: P0
depends_on: []

objective: |
  Prove one bounded claim.
"""
        self.assertEqual(
            validate_task_issue("[Zerion task] bounded proof", body),
            [],
        )
        self.assertIsNone(pinned_worker(body))
        self.assertEqual(reduce_task_status([]), "ready")

    def test_task_can_be_pinned_to_specific_worker(self):
        body = """[ORCHESTRATOR:v1]
task_id: alpha-security-0001
project: alpha
worker: alpha-security
priority: P0

objective: |
  Perform the security audit.
"""
        self.assertEqual(
            validate_task_issue("[Zerion task] security audit", body),
            [],
        )
        self.assertEqual(pinned_worker(body), "alpha-security")

    def test_legacy_assigned_body_is_accepted_during_migration(self):
        body = """[ORCHESTRATOR:v1]
task_id: alpha-old-0001
project: alpha
worker: alpha-theory
status: ASSIGNED
priority: P1

objective: |
  Complete legacy work.
"""
        self.assertEqual(
            validate_task_issue("[Zerion task] legacy task", body),
            [],
        )

    def test_invalid_task_status_is_rejected(self):
        body = """[ORCHESTRATOR:v1]
task_id: alpha-bad-0001
project: alpha
status: DONE
priority: P1

objective: |
  Invalid initial status.
"""
        errors = validate_task_issue("[Zerion task] bad task", body)
        self.assertTrue(any("status" in error for error in errors))

    def test_ack_establishes_worker_identity_and_claim(self):
        ack = """[WORKER:alpha-theory:v1]
task_id: alpha-proof-0001
status: ACK
dispatcher: pool-A
claimed_at: 2026-09-22T17:00:00Z
lease_hours: 3
"""
        self.assertEqual(validate_protocol_comment(ack), [])
        self.assertEqual(worker_from_event(ack), "alpha-theory")
        self.assertEqual(reduce_task_status([ack]), "claimed")

    def test_event_reduction_is_the_live_state_machine(self):
        comments = [
            """[WORKER:alpha-theory:v1]
task_id: t1
status: ACK
dispatcher: pool-A
claimed_at: now
lease_hours: 3
""",
            """[WORKER:alpha-theory:v1]
task_id: t1
status: BLOCKED
summary: waiting for dataset
""",
            """[ORCHESTRATOR-REVIEW:v1]
task_id: t1
status: REVISE
""",
            """[WORKER:alpha-theory:v1]
task_id: t1
status: ACK
dispatcher: pool-A
claimed_at: later
lease_hours: 3
""",
            """[WORKER:alpha-theory:v1]
task_id: t1
status: NEEDS_REVIEW
summary: new evidence is ready
""",
        ]
        self.assertEqual(reduce_task_status(comments), "needs_review")

    def test_ready_and_claimed_labels_are_derived_from_events(self):
        github = {
            "task_label": "zerion:task",
            "status_labels": {
                "ready": "zerion:ready",
                "claimed": "zerion:claimed",
                "blocked": "zerion:blocked",
                "needs_review": "zerion:needs-review",
                "accepted": "zerion:accepted",
                "revise": "zerion:revise",
                "rejected": "zerion:rejected",
            },
            "priority_label_prefix": "priority:",
        }
        body = """[ORCHESTRATOR:v1]
task_id: t1
project: alpha
priority: P0
"""
        self.assertEqual(
            desired_managed_labels(body, [], github),
            {"zerion:task", "zerion:ready", "priority:P0"},
        )

        ack = """[WORKER:alpha-theory:v1]
task_id: t1
status: ACK
dispatcher: pool-A
claimed_at: now
lease_hours: 3
"""
        self.assertEqual(
            desired_managed_labels(body, [ack], github),
            {"zerion:task", "zerion:claimed", "priority:P0"},
        )
        self.assertTrue(is_managed_label("zerion:ready", github))
        self.assertTrue(is_managed_label("priority:P1", github))
        self.assertFalse(is_managed_label("documentation", github))


if __name__ == "__main__":
    unittest.main()
