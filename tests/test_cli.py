from __future__ import annotations

import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import yaml

from zerion_orchestration.cli import main
from zerion_orchestration.core import validate_repository


class ZerionCLITests(unittest.TestCase):
    def test_init_validate_and_status(self):
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
            self.assertIn("alpha", registry["projects"])
            self.assertEqual(registry["entrypoint"], "AGENTS.md")

            for worker in project["active_workers"]:
                state_path = root / "coordination" / "state" / f"{worker}.yaml"
                self.assertTrue(state_path.exists())
                state = yaml.safe_load(state_path.read_text())
                self.assertEqual(state["worker"], worker)
                self.assertEqual(state["project"], "alpha")
                self.assertEqual(state["lifecycle"], "idle")
                self.assertEqual(state["claim"]["lease_hours"], 3)

            self.assertEqual(main(["--root", str(root), "validate"]), 0)

            status = io.StringIO()
            with contextlib.redirect_stdout(status):
                status_code = main(["--root", str(root), "status"])
            self.assertEqual(status_code, 0)
            self.assertIn("alpha", status.getvalue())
            self.assertIn("0/3", status.getvalue())

            json_status = io.StringIO()
            with contextlib.redirect_stdout(json_status):
                json_code = main(["--root", str(root), "status", "--json"])
            self.assertEqual(json_code, 0)
            self.assertIn('"states"', json_status.getvalue())
            self.assertIn('"registry"', json_status.getvalue())

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

    def test_mailbox_reference_drift_is_detected(self):
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
            state_path = root / "coordination" / "state" / "alpha-theory.yaml"

            project = yaml.safe_load(project_path.read_text())
            project["mailboxes"]["alpha-theory"] = 12
            project_path.write_text(yaml.safe_dump(project, sort_keys=False))

            state = yaml.safe_load(state_path.read_text())
            state["mailbox"]["pr"] = 13
            state_path.write_text(yaml.safe_dump(state, sort_keys=False))

            result = validate_repository(root)
            self.assertFalse(result.ok)
            self.assertTrue(
                any("mailbox PR differs" in e for e in result.errors)
            )


if __name__ == "__main__":
    unittest.main()
