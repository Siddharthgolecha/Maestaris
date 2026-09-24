from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class ReusableRuntimeTests(unittest.TestCase):
    def test_event_validator_reads_consumer_project_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            consumer = Path(tmp)
            coordination = consumer / "coordination"
            coordination.mkdir()
            (coordination / "maestaris.yaml").write_text(
                yaml.safe_dump(
                    {
                        "github": {
                            "task_title_prefix": "[Consumer task]",
                        }
                    }
                ),
                encoding="utf-8",
            )
            event = consumer / "event.json"
            event.write_text(
                json.dumps(
                    {
                        "issue": {
                            "title": "[Consumer task] bounded work",
                            "body": (
                                "[ORCHESTRATOR:v1]\n"
                                "task_id: consumer-1\n"
                                "project: consumer\n"
                                "priority: P1\n\n"
                                "objective: |\n  Verify external-root loading.\n"
                            ),
                        }
                    }
                ),
                encoding="utf-8",
            )
            env = os.environ.copy()
            env["MAESTARIS_PROJECT_ROOT"] = str(consumer)
            env["GITHUB_EVENT_PATH"] = str(event)
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "validate_github_event.py")],
                env=env,
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertIn("validation OK", result.stdout)

    def test_reusable_workflow_exposes_workflow_call(self):
        workflow = (ROOT / ".github" / "workflows" / "reusable-maestaris.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("workflow_call:", workflow)
        self.assertIn("MAESTARIS_PROJECT_ROOT", workflow)
        self.assertIn("issues: write", workflow)


if __name__ == "__main__":
    unittest.main()
