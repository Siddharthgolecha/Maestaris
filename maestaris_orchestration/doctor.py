from __future__ import annotations

import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
from typing import Any


def _command_version(command: str, *args: str) -> dict[str, Any]:
    path = shutil.which(command)
    if path is None:
        return {"available": False}
    try:
        proc = subprocess.run(
            [path, *args], text=True, capture_output=True, timeout=5, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"available": True, "version": None}
    first = (proc.stdout or proc.stderr).strip().splitlines()
    return {"available": True, "version": first[0] if first else None}


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def capability_report(root: Path) -> dict[str, Any]:
    """Return non-secret runtime observations suitable for durable handoff."""
    root = root.resolve()
    git = _command_version("git", "--version")
    gh = _command_version("gh", "--version")
    lean = _command_version("lake", "--version")

    # Environment variables are intentionally reported only as booleans. Never
    # include token values in doctor output.
    env_presence = {
        name: bool(os.environ.get(name))
        for name in ("GITHUB_ACTIONS", "CI")
    }

    return {
        "schema": 1,
        "kind": "maestaris-runtime-capability-report",
        "root": str(root),
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
            "python_executable": sys.executable,
        },
        "packages": {
            "maestaris": _package_version("maestaris-orchestration"),
            "pyyaml": _package_version("PyYAML"),
        },
        "local_tools": {
            "git": git,
            "gh": gh,
            "lake": lean,
        },
        "local_repository": {
            "git_directory_present": (root / ".git").exists(),
            "maestaris_registry_present": (root / "coordination" / "maestaris.yaml").exists(),
        },
        "runtime_signals": env_presence,
        "connected_services": {
            "github": "unknown",
            "note": (
                "Connected chat/API capabilities cannot be inferred from shell tools; "
                "record them separately from the runtime that invokes this command."
            ),
        },
        "verification": {
            "local_tool_absence_is_fatal": False,
            "hosted_ci_fallback": "Use repository Actions/checks when required verification is unavailable locally.",
            "claim_semantics": "Capabilities are observations, not evidence that a project claim is true.",
        },
    }


def render_report(report: dict[str, Any], *, as_json: bool = False) -> str:
    if as_json:
        return json.dumps(report, indent=2, sort_keys=True)
    lines = [
        "Maestaris runtime capability report",
        f"Python: {report['platform']['python']} ({report['platform']['system']} {report['platform']['machine']})",
    ]
    for name, item in report["local_tools"].items():
        state = "available" if item["available"] else "missing"
        suffix = f" - {item['version']}" if item.get("version") else ""
        lines.append(f"{name}: {state}{suffix}")
    lines.extend(
        [
            f"Maestaris registry: {'present' if report['local_repository']['maestaris_registry_present'] else 'missing'}",
            "Connected GitHub/API access: unknown from local shell; report separately.",
            "Missing local tools are not automatically fatal; use hosted CI when appropriate.",
        ]
    )
    return "\n".join(lines)
