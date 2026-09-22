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
    validate_protocol_comment,
    validate_task_issue,
)


class ZerionCLITests(unittest.TestCase):
    def test_init_validate_and_status_use_native_issues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(
                    [
                        "--root", str(root), "init", "alpha",
                        "--workers", "theory", "build", "audit",
                        "--repository", "example/alpha",
                    ]
                )
            self.assertEqual(code, 0)

            project_path = root / "coordination" / "projects" / "alpha.yaml"
            registry_path = root / "coordination" / "zerion.yaml"
            self.assertTrue(project_path.exists())
            self.assertTrue(registry_path.exists())
            self.assertTrue((root / "AGENTS.md").exists())

            project = yaml.safe_load(project_path.read_text())
            registry = yaml.safe_load(registry_path.read_text())

            self.assertEqual(
                project["active_workers"],
                ["alpha-theory", "alpha-build", "alpha-audit"],
            )
            self.assertEqual(project["auditor"], "alpha-audit")
            self.assertEqual(project["repository"], "example/alpha")
            self.assertEqual(project["control_plane"]["transport"], "github_issue")
            self.assertNotIn("mailboxes", project)
            self.assertIn("alpha", registry["projects"])
            self.assertEqual(registry["entrypoint"], "AGENTS.md")
            self.assertEqual(registry["protocol_version"], 2)
            self.assertEqual(registry["github"]["task_transport"], "issue")

            for worker in project["active_workers"]:
                agent_path = root / "coordination" / "agents" / f"{worker}.yaml"
                agent = yaml.safe_load(agent_path.read_text())
                self.assertEqual(
                    agent["control_plane"]["transport"],
                    "github_issue",
                )

                state_path = root / "coordination" / "state" / f"{worker}.yaml"
                self.assertTrue(state_path.exists())
                state = yaml.safe_load(state_path.read_text())
                self.assertEqual(state["worker"], worker)
                self.assertEqual(state["project"], "alpha")
                self.assertEqual(state["lifecycle"], "idle")
                self.assertEqual(state["claim"]["lease_hours"], 3)
                self.assertIn("issue", state["task"])
                self.assertIsNone(state["task"]["issue"])
                self.assertNotIn("mailbox", state)

            self.assertEqual(main(["--root", str(root), "validate"]), 0)

            status = io.StringIO()
            with contextlib.redirect_stdout(status):
                status_code = main(["--root", str(root), "status"])
            self.assertEqual(status_code, 0)
            self.assertIn("alpha", status.getvalue())
            self.assertIn("issues", status.getvalue())
            self.assertIn("0/3", status.getvalue())

            json_status = io.StringIO()
            with contextlib.redirect_stdout(json_status):
                json_code = main(["--root", str(root), "status", "--json"])
            self.assertEqual(json_code, 0)
            self.assertIn('"states"', json_status.getvalue())
            self.assertIn('"registry"', json_status.getvalue())
            self.assertIn('"warnings"', json_status.getvalue())

    def test_existing_agents_md_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agents_path = root / "AGENTS.md"
            agents_path.write_text("# Existing instructions\nDo not overwrite me.\n")

            self.assertEqual(
                main(
                    [
                        "--root", tmp, "init", "alpha",
                        "--workers", "theory",
                        "--repository", "example/alpha",
                    ]
                ),
                0,
            )
            self.assertEqual(
                agents_path.read_text(),
                "# Existing instructions\nDo not overwrite me.\n",
            )

    def test_duplicate_project_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            args = [
                "--root", tmp, "init", "alpha",
                "--workers", "theory",
                "--repository", "example/alpha",
            ]
            self.assertEqual(main(args), 0)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(args), 2)

    def test_invalid_name_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(
                    main(["--root", tmp, "init", "Bad Name", "--workers", "theory"]),
                    2,
                )

    def test_missing_state_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(
                main(
                    [
                        "--root", tmp, "init", "alpha",
                        "--workers", "theory",
                        "--repository", "example/alpha",
                    ]
                ),
                0,
            )
            state_path = root / "coordination" / "state" / "alpha-theory.yaml"
            state_path.unlink()

            result = validate_repository(root)
            self.assertFalse(result.ok)
            self.assertTrue(
                any("missing state index for alpha-theory" in e for e in result.errors)
            )

    def test_unregistered_project_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(
                main(
                    [
                        "--root", tmp, "init", "alpha",
                        "--workers", "theory",
                        "--repository", "example/alpha",
                    ]
                ),
                0,
            )
            registry_path = root / "coordination" / "zerion.yaml"
            registry = yaml.safe_load(registry_path.read_text())
            registry["projects"] = []
            registry_path.write_text(yaml.safe_dump(registry, sort_keys=False))

            result = validate_repository(root)
            self.assertFalse(result.ok)
            self.assertTrue(
                any("project 'alpha' is not registered" in e for e in result.errors)
            )

    def test_native_state_requires_issue_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(
                main(
                    [
                        "--root", tmp, "init", "alpha",
                        "--workers", "theory",
                        "--repository", "example/alpha",
                    ]
                ),
                0,
            )
            state_path = root / "coordination" / "state" / "alpha-theory.yaml"
            state = yaml.safe_load(state_path.read_text())
            del state["task"]["issue"]
            state_path.write_text(yaml.safe_dump(state, sort_keys=False))

            result = validate_repository(root)
            self.assertFalse(result.ok)
            self.assertTrue(
                any("native transport requires task.issue" in e for e in result.errors)
            )

    def test_legacy_mailbox_drift_is_still_detected_with_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(
                main(
                    [
                        "--root", tmp, "init", "alpha",
                        "--workers", "theory",
                        "--repository", "example/alpha",
                    ]
                ),
                0,
            )

            project_path = root / "coordination" / "projects" / "alpha.yaml"
            agent_path = root / "coordination" / "agents" / "alpha-theory.yaml"
            state_path = root / "coordination" / "state" / "alpha-theory.yaml"

            project = yaml.safe_load(project_path.read_text())
            project["control_plane"] = {"transport": "legacy_pull_request_mailbox"}
            project["mailboxes"] = {"alpha-theory": 12}
            project_path.write_text(yaml.safe_dump(project, sort_keys=False))

            agent = yaml.safe_load(agent_path.read_text())
            agent["control_plane"] = {"transport": "legacy_pull_request_mailbox"}
            agent["mailbox"] = {"transport": "pull_request", "pr": 12}
            agent_path.write_text(yaml.safe_dump(agent, sort_keys=False))

            state = yaml.safe_load(state_path.read_text())
            state["mailbox"] = {"pr": 13}
            state_path.write_text(yaml.safe_dump(state, sort_keys=False))

            result = validate_repository(root)
            self.assertFalse(result.ok)
            self.assertTrue(any("mailbox PR differs" in e for e in result.errors))
            self.assertTrue(any("deprecated" in w for w in result.warnings))

    def test_task_issue_protocol_validation(self):
        valid = """[ORCHESTRATOR:v1]
task_id: alpha-theory-0001
project: alpha
worker: alpha-theory
status: ASSIGNED
priority: P1

## Objective

Prove one bounded claim.
"""
        self.assertEqual(
            validate_task_issue("[Zerion task] prove bounded claim", valid),
            [],
        )

        errors = validate_task_issue(
            "[Zerion task] malformed",
            "[ORCHESTRATOR:v1]\nstatus: DONE\n",
        )
        self.assertTrue(any("task_id" in e for e in errors))
        self.assertTrue(any("status must be ASSIGNED" in e for e in errors))

    def test_protocol_comment_validation(self):
        ack = """[WORKER:alpha-theory:v1]
task_id: alpha-theory-0001
status: ACK
dispatcher: pool-A
claimed_at: 2026-09-22T16:00:00Z
lease_hours: 3
"""
        self.assertEqual(validate_protocol_comment(ack), [])

        done = """[WORKER:alpha-theory:v1]
task_id: alpha-theory-0001
status: DONE
summary: completed with CI evidence
"""
        self.assertEqual(validate_protocol_comment(done), [])

        review = """[ORCHESTRATOR-REVIEW:v1]
task_id: alpha-theory-0001
status: ACCEPTED
"""
        self.assertEqual(validate_protocol_comment(review), [])

        bad_ack = """[WORKER:alpha-theory:v1]
task_id: alpha-theory-0001
status: ACK
"""
        errors = validate_protocol_comment(bad_ack)
        self.assertTrue(any("dispatcher" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
