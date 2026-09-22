from __future__ import annotations

import contextlib
import io
from pathlib import Path
import tempfile
import unittest

import yaml

from zerion_orchestration.cli import main


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
            self.assertTrue(project_path.exists())
            project = yaml.safe_load(project_path.read_text())
            self.assertEqual(
                project["active_workers"],
                ["alpha-theory", "alpha-build", "alpha-audit"],
            )
            self.assertEqual(project["auditor"], "alpha-audit")
            self.assertEqual(project["repository"], "example/alpha")

            self.assertEqual(main(["--root", str(root), "validate"]), 0)

            status = io.StringIO()
            with contextlib.redirect_stdout(status):
                status_code = main(["--root", str(root), "status"])
            self.assertEqual(status_code, 0)
            self.assertIn("alpha", status.getvalue())
            self.assertIn("0/3", status.getvalue())

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


if __name__ == "__main__":
    unittest.main()
