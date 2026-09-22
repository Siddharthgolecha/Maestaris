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
    reduce_task_status,
    validate_protocol_comment,
    validate_task_issue,
)


class ZerionV05Tests(unittest.TestCase):
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

            self.assertEqual(registry["protocol_version"], 3)
            self.assertEqual(registry["github"]["task_transport"], "issue")
            self.assertEqual(registry["github"]["task_label"], "zerion:task")
            self.assertEqual(
                registry["github"]["projects"]["auto_add_filter"],
                'is:issue label:"zerion:task"',
            )

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

            status = io.StringIO()
            with contextlib.redirect_stdout(status):
                self.assertEqual(main(["--root", str(root), "status"]), 0)
            self.assertIn("live task state is in GitHub", status.getvalue())
            self.assertIn("alpha", status.getvalue())

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

    def test_protocol_v3_rejects_shadow_state_files(self):
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

    def test_task_issue_and_comment_validation(self):
        body = """[ORCHESTRATOR:v1]
task_id: alpha-theory-0001
project: alpha
worker: alpha-theory
status: ASSIGNED
priority: P0

objective: |
  Prove one bounded claim.
"""
        self.assertEqual(
            validate_task_issue("[Zerion task] bounded proof", body),
            [],
        )

        ack = """[WORKER:alpha-theory:v1]
task_id: alpha-theory-0001
status: ACK
dispatcher: pool-A
claimed_at: 2026-09-22T17:00:00Z
lease_hours: 3
"""
        self.assertEqual(validate_protocol_comment(ack), [])

        done = """[WORKER:alpha-theory:v1]
task_id: alpha-theory-0001
status: DONE
summary: proof committed and checked
"""
        self.assertEqual(validate_protocol_comment(done), [])

        review = """[ORCHESTRATOR-REVIEW:v1]
task_id: alpha-theory-0001
status: ACCEPTED
"""
        self.assertEqual(validate_protocol_comment(review), [])

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

    def test_managed_labels_are_derived_from_events(self):
        github = {
            "task_label": "zerion:task",
            "status_labels": {
                "assigned": "zerion:assigned",
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
worker: alpha-theory
status: ASSIGNED
priority: P0
"""
        comments = [
            """[WORKER:alpha-theory:v1]
task_id: t1
status: ACK
dispatcher: pool-A
claimed_at: now
lease_hours: 3
"""
        ]

        labels = desired_managed_labels(body, comments, github)
        self.assertEqual(
            labels,
            {"zerion:task", "zerion:claimed", "priority:P0"},
        )
        self.assertTrue(is_managed_label("zerion:blocked", github))
        self.assertTrue(is_managed_label("priority:P1", github))
        self.assertFalse(is_managed_label("documentation", github))


if __name__ == "__main__":
    unittest.main()
