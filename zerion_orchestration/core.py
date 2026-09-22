from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PROJECT_STATES = {"active", "waiting", "dormant", "completed"}
AGENT_STATES = {"active", "assigned", "blocked", "waiting", "dormant", "completed"}
WORKER_LIFECYCLES = {
    "idle",
    "assigned",
    "claimed",
    "done",
    "blocked",
    "needs_review",
    "dormant",
}


@dataclass
class ValidationResult:
    registry: dict[str, Any]
    projects: dict[str, dict[str, Any]]
    agents: dict[str, dict[str, Any]]
    states: dict[str, dict[str, Any]]
    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def coordination_paths(root: Path) -> tuple[Path, Path]:
    base = root / "coordination"
    return base / "projects", base / "agents"


def ensure_layout(root: Path) -> None:
    for rel in (
        "coordination/projects",
        "coordination/agents",
        "coordination/state",
        "coordination/mailboxes",
    ):
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


def build_registry() -> dict[str, Any]:
    return {
        "schema": 1,
        "protocol_version": 1,
        "entrypoint": "AGENTS.md",
        "canonical_branch": "main",
        "orchestrator": "orchestrator",
        "defaults": {"ack_lease_hours": 3},
        "pools": {
            "A": {"max_tasks_per_run": 1},
            "B": {"max_tasks_per_run": 1},
        },
        "projects": [],
    }


def build_state(worker: str, project: str, lease_hours: int = 3) -> dict[str, Any]:
    return {
        "schema": 1,
        "worker": worker,
        "project": project,
        "lifecycle": "idle",
        "mailbox": {"pr": None},
        "task": {
            "id": None,
            "status": None,
            "priority": None,
            "task_pr": None,
        },
        "claim": {
            "dispatcher": None,
            "claimed_at": None,
            "lease_hours": lease_hours,
        },
        "result": {
            "status": None,
            "commit": None,
            "task_pr": None,
        },
        "last_review": {
            "task_id": None,
            "status": None,
            "reviewed_at": None,
        },
        "updated_at": None,
    }


def validate_repository(root: Path) -> ValidationResult:
    projects_dir, agents_dir = coordination_paths(root)
    base = root / "coordination"
    state_dir = base / "state"
    registry_path = base / "zerion.yaml"

    errors: list[str] = []
    registry: dict[str, Any] = {}
    projects: dict[str, dict[str, Any]] = {}
    agents: dict[str, dict[str, Any]] = {}
    states: dict[str, dict[str, Any]] = {}

    if not registry_path.exists():
        errors.append(f"{registry_path}: missing Zerion registry")
    else:
        try:
            registry = load_yaml(registry_path)
        except Exception as exc:
            errors.append(str(exc))

    if registry:
        if registry.get("schema") != 1:
            errors.append(f"{registry_path}: schema must be 1")
        if registry.get("entrypoint") != "AGENTS.md":
            errors.append(f"{registry_path}: entrypoint must be AGENTS.md")
        if not isinstance(registry.get("protocol_version"), int):
            errors.append(f"{registry_path}: protocol_version must be an integer")
        defaults = registry.get("defaults") or {}
        lease = defaults.get("ack_lease_hours")
        if not isinstance(lease, int) or lease < 1:
            errors.append(f"{registry_path}: defaults.ack_lease_hours must be >= 1")
        pools = registry.get("pools")
        if not isinstance(pools, dict) or not pools:
            errors.append(f"{registry_path}: pools must be a non-empty mapping")
        registered_projects = registry.get("projects")
        if not isinstance(registered_projects, list):
            errors.append(f"{registry_path}: projects must be a list")

    if not projects_dir.exists():
        errors.append(f"{projects_dir}: missing project registry")
    if not agents_dir.exists():
        errors.append(f"{agents_dir}: missing agent registry")
    if not state_dir.exists():
        errors.append(f"{state_dir}: missing state index")

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

    for path in sorted(state_dir.glob("*.yaml")) if state_dir.exists() else []:
        try:
            data = load_yaml(path)
        except Exception as exc:
            errors.append(str(exc))
            continue
        worker = data.get("worker")
        if not worker:
            errors.append(f"{path}: missing worker")
            continue
        worker = str(worker)
        states[worker] = data
        if path.stem != worker:
            errors.append(f"{path}: filename must match worker {worker!r}")
        if data.get("schema") != 1:
            errors.append(f"{path}: schema must be 1")
        if data.get("lifecycle") not in WORKER_LIFECYCLES:
            errors.append(f"{path}: invalid lifecycle {data.get('lifecycle')!r}")
        if worker not in agents:
            errors.append(f"{path}: unknown worker {worker!r}")
        project = data.get("project")
        if project not in projects:
            errors.append(f"{path}: unknown project {project!r}")
        elif worker in agents and agents[worker].get("project") != project:
            errors.append(
                f"{path}: project {project!r} does not match agent project "
                f"{agents[worker].get('project')!r}"
            )

        mailbox = data.get("mailbox") or {}
        if not isinstance(mailbox, dict) or "pr" not in mailbox:
            errors.append(f"{path}: mailbox.pr is required")
        claim = data.get("claim") or {}
        if not isinstance(claim, dict):
            errors.append(f"{path}: claim must be a mapping")
        else:
            lease = claim.get("lease_hours")
            if not isinstance(lease, int) or lease < 1:
                errors.append(f"{path}: claim.lease_hours must be >= 1")

    if registry:
        listed = set(map(str, registry.get("projects") or []))
        present = set(projects)
        for missing in sorted(listed - present):
            errors.append(f"{registry_path}: registered project {missing!r} has no project file")
        for unlisted in sorted(present - listed):
            errors.append(f"{registry_path}: project {unlisted!r} is not registered")

        orchestrator = registry.get("orchestrator")
        if orchestrator not in agents:
            errors.append(f"{registry_path}: orchestrator {orchestrator!r} is not registered")

        pools = set((registry.get("pools") or {}).keys())
        for agent_name, agent in agents.items():
            pool = agent.get("dispatcher_pool")
            if pool not in (None, "none") and pool not in pools:
                errors.append(
                    f"agent {agent_name}: dispatcher_pool {pool!r} is not in coordination/zerion.yaml"
                )

    required_workers: set[str] = set()
    for project_name, project in projects.items():
        active = project.get("active_workers") or []
        dormant = project.get("dormant_workers") or []
        if not isinstance(active, list) or not isinstance(dormant, list):
            errors.append(f"project {project_name}: worker lists must be arrays")
            continue
        named = set(map(str, active)) | set(map(str, dormant))
        required_workers |= named
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
        for worker in named:
            if worker not in states:
                errors.append(f"project {project_name}: missing state index for {worker}")
                continue
            project_pr = mailboxes.get(worker)
            agent_pr = ((agents.get(worker) or {}).get("mailbox") or {}).get("pr")
            state_pr = ((states.get(worker) or {}).get("mailbox") or {}).get("pr")
            configured = [value for value in (project_pr, agent_pr, state_pr) if value is not None]
            if configured and any(value != configured[0] for value in configured[1:]):
                errors.append(
                    f"worker {worker}: mailbox PR differs across project/agent/state registry"
                )

    for worker in sorted(set(states) - required_workers):
        errors.append(f"state {worker}: worker is not listed by any project")

    return ValidationResult(
        registry=registry,
        projects=projects,
        agents=agents,
        states=states,
        errors=errors,
    )


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
        "project_paths": ["coordination/projects", "coordination/agents", "coordination/state"],
        "current_task": None,
        "current_objective": None,
    }
