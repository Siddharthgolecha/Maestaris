from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PROJECT_STATES = {"active", "waiting", "dormant", "completed"}
AGENT_STATES = {"active", "assigned", "blocked", "waiting", "dormant", "completed"}


@dataclass
class ValidationResult:
    projects: dict[str, dict[str, Any]]
    agents: dict[str, dict[str, Any]]
    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def coordination_paths(root: Path) -> tuple[Path, Path]:
    base = root / "coordination"
    return base / "projects", base / "agents"


def ensure_layout(root: Path) -> None:
    for rel in ("coordination/projects", "coordination/agents", "coordination/mailboxes"):
        (root / rel).mkdir(parents=True, exist_ok=True)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return data


def dump_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def validate_name(value: str, label: str = "name") -> None:
    if not NAME_RE.fullmatch(value):
        raise ValueError(
            f"invalid {label} {value!r}: use lowercase letters, digits, and hyphens"
        )


def validate_repository(root: Path) -> ValidationResult:
    projects_dir, agents_dir = coordination_paths(root)
    errors: list[str] = []
    projects: dict[str, dict[str, Any]] = {}
    agents: dict[str, dict[str, Any]] = {}

    if not projects_dir.exists():
        errors.append(f"{projects_dir}: missing project registry")
    if not agents_dir.exists():
        errors.append(f"{agents_dir}: missing agent registry")

    for path in sorted(projects_dir.glob("*.yaml")) if projects_dir.exists() else []:
        try:
            data = load_yaml(path)
        except Exception as exc:
            errors.append(str(exc))
            continue
        name = data.get("project")
        if not name:
            errors.append(f"{path}: missing project")
            continue
        projects[str(name)] = data
        if data.get("schema") != 1:
            errors.append(f"{path}: schema must be 1")
        if data.get("status") not in PROJECT_STATES:
            errors.append(f"{path}: invalid project status {data.get('status')!r}")
        try:
            validate_name(str(name), "project")
        except ValueError as exc:
            errors.append(f"{path}: {exc}")

    for path in sorted(agents_dir.glob("*.yaml")) if agents_dir.exists() else []:
        try:
            data = load_yaml(path)
        except Exception as exc:
            errors.append(str(exc))
            continue
        name = data.get("agent")
        if not name:
            errors.append(f"{path}: missing agent")
            continue
        agents[str(name)] = data
        if data.get("schema") != 1:
            errors.append(f"{path}: schema must be 1")
        if data.get("status") not in AGENT_STATES:
            errors.append(f"{path}: invalid agent status {data.get('status')!r}")
        try:
            validate_name(str(name), "agent")
        except ValueError as exc:
            errors.append(f"{path}: {exc}")
        project = data.get("project")
        if project != "*" and project not in projects:
            errors.append(f"{path}: unknown project {project!r}")

    for project_name, project in projects.items():
        active = project.get("active_workers") or []
        dormant = project.get("dormant_workers") or []
        if not isinstance(active, list) or not isinstance(dormant, list):
            errors.append(f"project {project_name}: worker lists must be arrays")
            continue
        named = set(map(str, active)) | set(map(str, dormant))
        missing = sorted(named - set(agents))
        if missing:
            errors.append(
                f"project {project_name}: unregistered workers: {', '.join(missing)}"
            )
        mailboxes = project.get("mailboxes") or {}
        if not isinstance(mailboxes, dict):
            errors.append(f"project {project_name}: mailboxes must be a mapping")
            continue
        unknown = sorted(set(map(str, mailboxes)) - named)
        if unknown:
            errors.append(
                f"project {project_name}: mailboxes for unknown workers: {', '.join(unknown)}"
            )

    return ValidationResult(projects=projects, agents=agents, errors=errors)


def infer_auditor(worker_ids: list[str]) -> str | None:
    for worker in worker_ids:
        if "audit" in worker:
            return worker
    return None


def build_project(
    project: str,
    title: str,
    repository: str,
    runtime: str,
    workers: list[str],
) -> dict[str, Any]:
    return {
        "schema": 1,
        "project": project,
        "title": title,
        "status": "active",
        "repository": repository,
        "runtime": runtime,
        "canonical_paths": ["README.md"],
        "orchestrator": "orchestrator",
        "auditor": infer_auditor(workers),
        "active_workers": workers,
        "dormant_workers": [],
        "mailboxes": {worker: None for worker in workers},
    }


def build_agent(worker: str, project: str, role: str, pool: str) -> dict[str, Any]:
    return {
        "schema": 1,
        "agent": worker,
        "project": project,
        "role": role,
        "dispatcher_pool": pool,
        "status": "active",
        "mailbox": {"transport": "pull_request", "pr": None},
        "project_paths": ["."],
        "current_task": None,
        "current_objective": None,
    }


def build_orchestrator() -> dict[str, Any]:
    return {
        "schema": 1,
        "agent": "orchestrator",
        "project": "*",
        "role": "project-orchestration",
        "dispatcher_pool": "none",
        "status": "active",
        "mailbox": {"transport": "none", "pr": None},
        "project_paths": ["coordination/projects", "coordination/agents"],
        "current_task": None,
        "current_objective": None,
    }
