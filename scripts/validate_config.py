#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

try:
    import yaml
except ImportError:
    print("PyYAML is required: python -m pip install pyyaml", file=sys.stderr)
    raise SystemExit(2)

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ROOT / "coordination" / "projects"
AGENTS = ROOT / "coordination" / "agents"

ALLOWED_PROJECT = {"active", "waiting", "dormant", "completed"}
ALLOWED_AGENT = {"active", "assigned", "blocked", "waiting", "dormant", "completed"}

errors: list[str] = []

def load(path: Path):
    try:
        with path.open() as f:
            return yaml.safe_load(f)
    except Exception as exc:
        errors.append(f"{path}: could not parse YAML: {exc}")
        return None

projects = {}
for path in sorted(PROJECTS.glob("*.yaml")):
    data = load(path)
    if not isinstance(data, dict):
        errors.append(f"{path}: expected a mapping")
        continue
    name = data.get("project")
    if not name:
        errors.append(f"{path}: missing project")
        continue
    projects[name] = data
    if data.get("schema") != 1:
        errors.append(f"{path}: schema must be 1")
    if data.get("status") not in ALLOWED_PROJECT:
        errors.append(f"{path}: invalid project status {data.get('status')!r}")

agents = {}
for path in sorted(AGENTS.glob("*.yaml")):
    data = load(path)
    if not isinstance(data, dict):
        errors.append(f"{path}: expected a mapping")
        continue
    name = data.get("agent")
    if not name:
        errors.append(f"{path}: missing agent")
        continue
    agents[name] = data
    if data.get("schema") != 1:
        errors.append(f"{path}: schema must be 1")
    if data.get("status") not in ALLOWED_AGENT:
        errors.append(f"{path}: invalid agent status {data.get('status')!r}")
    project = data.get("project")
    if project != "*" and project not in projects:
        errors.append(f"{path}: unknown project {project!r}")

for project_name, project in projects.items():
    named = set(project.get("active_workers", [])) | set(project.get("dormant_workers", []))
    missing = sorted(named - set(agents))
    if missing:
        errors.append(f"project {project_name}: unregistered workers: {', '.join(missing)}")
    mailbox_keys = set((project.get("mailboxes") or {}).keys())
    unknown_mailboxes = sorted(mailbox_keys - named)
    if unknown_mailboxes:
        errors.append(f"project {project_name}: mailboxes for unknown workers: {', '.join(unknown_mailboxes)}")

if errors:
    print("Zerion configuration validation FAILED")
    for e in errors:
        print(f"- {e}")
    raise SystemExit(1)

print(f"Zerion configuration validation OK: {len(projects)} project(s), {len(agents)} agent(s)")
