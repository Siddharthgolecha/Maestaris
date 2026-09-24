from __future__ import annotations

import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from maestaris_orchestration.cli import main
from maestaris_orchestration.doctor import capability_report


class RuntimeDoctorTests(unittest.TestCase):
    def test_report_is_machine_readable_and_does_not_emit_secret_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "coordination").mkdir()
            (root / "coordination" / "maestaris.yaml").write_text("schema: 1\n")
            secret = "DO-NOT-LEAK-THIS-TOKEN"
            with mock.patch.dict(os.environ, {"GITHUB_TOKEN": secret}, clear=False):
                report = capability_report(root)
                encoded = json.dumps(report)
            self.assertEqual(report["schema"], 1)
            self.assertEqual(report["kind"], "maestaris-runtime-capability-report")
            self.assertTrue(report["local_repository"]["maestaris_registry_present"])
            self.assertNotIn(secret, encoded)
            self.assertNotIn("GITHUB_TOKEN", report["runtime_signals"])

    def test_doctor_json_cli_succeeds_even_when_optional_tools_are_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            with mock.patch("maestaris_orchestration.doctor.shutil.which", return_value=None):
                with contextlib.redirect_stdout(out):
                    code = main(["--root", tmp, "doctor", "--json"])
            self.assertEqual(code, 0)
            report = json.loads(out.getvalue())
            self.assertFalse(report["local_tools"]["git"]["available"])
            self.assertFalse(report["verification"]["local_tool_absence_is_fatal"])
            self.assertIn("Actions", report["verification"]["hosted_ci_fallback"])


if __name__ == "__main__":
    unittest.main()
