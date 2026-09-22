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
CONTROL_PLANE_TRANSPORTS = {"github_issue", "legacy_pull_request_mailbox"}


@dataclass
class ValidationResult:
    registry: dict[str, Any]
    projects: dict[str, dict[str, Any]]
    agents: dict[str, dict[str, Any]]
    states: dict[str, dict[str, Any]]
    errors: list[str]
    warnings: list[str]

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


DEFAULT_AGENTS_MD = """# Agent operating instructions

This repository uses Zerion's repository-first orchestration protocol.

Start with `coordination/zerion.yaml`, resolve the project and worker, then read the project registry, agent configuration, worker state index, current GitHub task Issue, canonical project paths, and actual task evidence.

Repository/GitHub evidence is authoritative over chat memory.

For the preferred GitHub-native transport, a task Issue is the control-plane object. ACKs, worker terminal reports, and orchestrator review events are comments on that Issue. Substantive work belongs in a linked task branch and draft pull request. CI/checks, commits, proofs, experiments, and artifacts are the evidence.

`coordination/state/<worker>.yaml` is only a fast index. If it disagrees with newer Issue/PR evidence, use the newer durable evidence and repair the index.

Legacy PR-backed mailboxes may still exist in older Zerion projects. Treat them as compatibility transport, not the preferred model.

Preserve stable task IDs, ACK ownership, negative results, and idempotency under retries.
"""


def ensure_agents_entrypoint(root: Path) -> bool:
    path = root / "AGENTS.md"
    if path.exists():
        return False
    path.write_text(DEFAULT_AGENTS_MD, encoding="utf-8")
    return True


def build_registry() -> dict[str, Any]:
    return {
        "schema": 1,
        "protocol_version": 2,
        "entrypoint": "AGENTS.md",
        "canonical_branch": "main",
        "orchestrator": "orchestrator",
        "defaults": {"ack_lease_hours": 3},
        "github": {
            "task_transport": "issue",
            "task_issue": {
                "title_prefix": "[Zerion task]",
                "accepted_state_reason": "completed",
                "rejected_state_reason": "not_planned",
            },
            "task_pull_request": {
                "draft_on_start": True,
                "branch_prefix": "zerion/task",
                "link_keyword": "Resolves",
            },
            "native_reviews": {
                "enabled": True,
                "accepted": "APPROVE",
                "revise": "REQUEST_CHANGES",
                "same_actor_fallback": "COMMENT",
            },
        },
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
        "task": {
            "id": None,
            "issue": None,
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


def _project_transport(project: dict[str, Any]) -> str | None:
    control_plane = project.get("control_plane")
    if isinstance(control_plane, dict) and control_plane.get("transport"):
        return str(control_plane["transport"])
    if "mailboxes" in project:
        return "legacy_pull_request_mailbox"
    return None


def _agent_transport(agent: dict[str, Any]) -> str | None:
    control_plane = agent.get("control_plane")
    if isinstance(control_plane, dict) and control_plane.get("transport"):
        return str(control_plane["transport"])
    if "mailbox" in agent:
        return "legacy_pull_request_mailbox"
    return None


def validate_repository(root: Path) -> ValidationResult:
    projects_dir, agents_dir = coordination_paths(root)
    base = root / "coordination"
    state_dir = base / "state"
    registry_path = base / "zerion.yaml"

    errors: list[str] = []
    warnings: list[str] = []
    registry: dict[str, Any] = {}
    projects: dict[str, dict[str, Any]] = {}
    agents: dict[str, dict[str, Any]] = {}
    states: dict[str, dict[str, Any]] = {}

    agents_entrypoint = root / "AGENTS.md"
    if not agents_entrypoint.exists():
        errors.append(f"{agents_entrypoint}: missing agent entry point")

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
        protocol_version = registry.get("protocol_version")
        if not isinstance(protocol_version, int):
            errors.append(f"{registry_path}: protocol_version must be an integer")
        elif protocol_version < 1:
            errors.append(f"{registry_path}: protocol_version must be >= 1")

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

        if isinstance(protocol_version, int) and protocol_version >= 2:
            github = registry.get("github")
            if not isinstance(github, dict):
                errors.append(f"{registry_path}: protocol v2 requires github configuration")
            else:
                if github.get("task_transport") != "issue":
                    errors.append(f"{registry_path}: github.task_transport must be 'issue'")
                task_issue = github.get("task_issue") or {}
                if not task_issue.get("title_prefix"):
                    errors.append(f"{registry_path}: github.task_issue.title_prefix is required")
                task_pr = github.get("task_pull_request") or {}
                if not task_pr.get("branch_prefix"):
                    errors.append(f"{registry_path}: github.task_pull_request.branch_prefix is required")

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

        transport = _project_transport(data)
        if transport not in CONTROL_PLANE_TRANSPORTS:
            errors.append(
                f"{path}: control-plane transport must be one of "
                f"{sorted(CONTROL_PLANE_TRANSPORTS)}"
            )
        elif transport == "legacy_pull_request_mailbox":
            warnings.append(
                f"{path}: legacy PR-mailbox transport is deprecated; prefer github_issue"
            )

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
        name = str(name)
        agents[name] = data
        if data.get("schema") != 1:
            errors.append(f"{path}: schema must be 1")
        if data.get("status") not in AGENT_STATES:
            errors.append(f"{path}: invalid agent status {data.get('status')!r}")
        try:
            validate_name(name, "agent")
        except ValueError as exc:
            errors.append(f"{path}: {exc}")

        project = data.get("project")
        if project != "*" and project not in projects:
            errors.append(f"{path}: unknown project {project!r}")

        if project != "*":
            transport = _agent_transport(data)
            if transport not in CONTROL_PLANE_TRANSPORTS:
                errors.append(
                    f"{path}: control-plane transport must be one of "
                    f"{sorted(CONTROL_PLANE_TRANSPORTS)}"
                )
            elif transport == "legacy_pull_request_mailbox":
                warnings.append(
                    f"{path}: legacy PR-mailbox transport is deprecated; prefer github_issue"
                )

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

        task = data.get("task")
        if not isinstance(task, dict):
            errors.append(f"{path}: task must be a mapping")
        else:
            for key in ("id", "status", "priority", "task_pr"):
                if key not in task:
                    errors.append(f"{path}: task.{key} is required")

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
                    f"agent {agent_name}: dispatcher_pool {pool!r} "
                    "is not in coordination/zerion.yaml"
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

        transport = _project_transport(project)

        if transport == "legacy_pull_request_mailbox":
            mailboxes = project.get("mailboxes") or {}
            if not isinstance(mailboxes, dict):
                errors.append(f"project {project_name}: mailboxes must be a mapping")
                mailboxes = {}
            unknown = sorted(set(map(str, mailboxes)) - named)
            if unknown:
                errors.append(
                    f"project {project_name}: mailboxes for unknown workers: "
                    f"{', '.join(unknown)}"
                )

        for worker in named:
            if worker not in states:
                errors.append(f"project {project_name}: missing state index for {worker}")
                continue

            agent = agents.get(worker) or {}
            agent_transport = _agent_transport(agent)
            if agent_transport != transport:
                errors.append(
                    f"worker {worker}: agent transport {agent_transport!r} "
                    f"does not match project transport {transport!r}"
                )

            state = states[worker]
            task = state.get("task") or {}

            if transport == "github_issue":
                if "issue" not in task:
                    errors.append(f"worker {worker}: native transport requires task.issue")
                issue = task.get("issue")
                if issue is not None and (not isinstance(issue, int) or issue < 1):
                    errors.append(f"worker {worker}: task.issue must be a positive integer or null")
            elif transport == "legacy_pull_request_mailbox":
                mailboxes = project.get("mailboxes") or {}
                project_pr = mailboxes.get(worker)
                agent_pr = (agent.get("mailbox") or {}).get("pr")
                state_pr = (state.get("mailbox") or {}).get("pr")
                configured = [
                    value for value in (project_pr, agent_pr, state_pr)
                    if value is not None
                ]
                if configured and any(value != configured[0] for value in configured[1:]):
                    errors.append(
                        f"worker {worker}: mailbox PR differs across "
                        "project/agent/state registry"
                    )

    for worker in sorted(set(states) - required_workers):
        errors.append(f"state {worker}: worker is not listed by any project")

    return ValidationResult(
        registry=registry,
        projects=projects,
        agents=agents,
        states=states,
        errors=errors,
        warnings=warnings,
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
        "control_plane": {"transport": "github_issue"},
        "active_workers": workers,
        "dormant_workers": [],
    }


def build_agent(worker: str, project: str, role: str, pool: str) -> dict[str, Any]:
    return {
        "schema": 1,
        "agent": worker,
        "project": project,
        "role": role,
        "dispatcher_pool": pool,
        "status": "active",
        "control_plane": {"transport": "github_issue"},
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
        "project_paths": [
            "coordination/projects",
            "coordination/agents",
            "coordination/state",
        ],
        "current_task": None,
        "current_objective": None,
    }
