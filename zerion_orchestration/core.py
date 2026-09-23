from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
from typing import Any

import yaml

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PROJECT_STATES = {"active", "waiting", "dormant", "completed"}
AGENT_STATES = {"active", "blocked", "waiting", "dormant", "completed"}


@dataclass
class ValidationResult:
    registry: dict[str, Any]
    projects: dict[str, dict[str, Any]]
    agents: dict[str, dict[str, Any]]
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def ensure_layout(root: Path) -> None:
    for rel in ("coordination/projects", "coordination/agents"):
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


DEFAULT_AGENTS_MD = """# Zerion agent operating instructions

This repository uses Zerion's GitHub-native orchestration protocol.

Read `coordination/zerion.yaml`, the relevant project and agent configuration, then discover live work from GitHub task Issues. Do not expect mutable worker-state YAML: Issues, comments, pull requests, checks, and artifacts are the live system of record.

Repository/GitHub evidence is authoritative over chat memory.

For ordinary ChatGPT conversations, GitHub events do not wake the chat. Scheduled or manual workers poll GitHub. An open task Issue is READY and unowned by default; the first valid ACK establishes the worker lease. Linked pull requests carry substantive repository work.

Start from the root AGENTS.md in this repository for the complete bootstrap.
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
        "protocol_version": 4,
        "entrypoint": "AGENTS.md",
        "canonical_branch": "main",
        "orchestrator": "orchestrator",
        "defaults": {
            "ack_lease_hours": 3,
            "max_pending_reviews_per_dispatcher": 1,
        },
        "github": {
            "task_transport": "issue",
            "task_title_prefix": "[Zerion task]",
            "task_label": "zerion:task",
            "status_labels": {
                "ready": "zerion:ready",
                "claimed": "zerion:claimed",
                "blocked": "zerion:blocked",
                "needs_review": "zerion:needs-review",
                "accepted": "zerion:accepted",
                "revise": "zerion:revise",
                "rejected": "zerion:rejected",
            },
            "priority_label_prefix": "priority:",
            "task_pull_request": {
                "draft_on_start": True,
                "branch_prefix": "zerion/task",
                "link_keyword": "Resolves",
            },
            "native_reviews": {
                "accepted": "APPROVE",
                "revise": "REQUEST_CHANGES",
                "same_actor_fallback": "COMMENT",
            },
            "projects": {
                "optional": True,
                "auto_add_filter": 'is:issue label:"zerion:task"',
                "field_sync": {
                    "enabled": False,
                    "project_id_env": "ZERION_PROJECT_ID",
                    "token_env": "ZERION_PROJECT_TOKEN",
                    "fields": {
                        "priority": "Priority",
                        "status": "Status",
                        "worker": "Worker",
                        "dispatcher": "Dispatcher",
                        "runtime": "Runtime",
                    },
                    "mappings": {
                        "priority": {"P0": "P0", "P1": "P1", "P2": "P2"},
                        "status": {
                            "ready": "Todo",
                            "claimed": "In Progress",
                            "blocked": "In Progress",
                            "needs_review": "In Progress",
                            "revise": "In Progress",
                            "accepted": "Done",
                            "rejected": "Done",
                        },
                    },
                },
            },
        },
        "pools": {
            "A": {"max_tasks_per_run": 1},
            "B": {"max_tasks_per_run": 1},
        },
        "scheduler_bootstrap": {
            "enabled": True,
            "source": "pools",
            "cadence": "hourly",
            "reconcile_existing": True,
            "instance_template": "zerion-{runtime}-pool-{pool}",
            "schedule_minutes": {
                "chatgpt": {"A": 22, "B": 52},
                "gemini-spark": {"A": 37, "B": 7},
            },
            "orchestrator_schedule": {
                "enabled": True,
                "instance_template": "zerion-{runtime}-orchestrator",
                "schedule_minutes": {
                    "chatgpt": 7,
                    "gemini-spark": 22,
                },
            },
        },
        "projects": [],
    }


def infer_repository_from_git(root: Path) -> str:
    try:
        proc = subprocess.run(
            ["git", "config", "--get", "remote.origin.url"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return "owner/repository"

    if proc.returncode:
        return "owner/repository"

    url = proc.stdout.strip()
    patterns = (
        r"https?://github\.com/([^/]+/[^/]+?)(?:\.git)?$",
        r"git@github\.com:([^/]+/[^/]+?)(?:\.git)?$",
        r"ssh://git@github\.com/([^/]+/[^/]+?)(?:\.git)?$",
    )
    for pattern in patterns:
        match = re.match(pattern, url)
        if match:
            return match.group(1)
    return "owner/repository"


def _legacy_files(root: Path) -> list[Path]:
    found: list[Path] = []
    for rel in ("coordination/state", "coordination/mailboxes"):
        path = root / rel
        if path.exists():
            found.extend(p for p in path.rglob("*") if p.is_file())
    for rel in (
        "coordination/schema/state.schema.json",
        "coordination/templates/STATE_TEMPLATE.yaml",
    ):
        path = root / rel
        if path.exists():
            found.append(path)
    return found


def validate_repository(root: Path) -> ValidationResult:
    base = root / "coordination"
    registry_path = base / "zerion.yaml"
    projects_dir = base / "projects"
    agents_dir = base / "agents"

    errors: list[str] = []
    warnings: list[str] = []
    registry: dict[str, Any] = {}
    projects: dict[str, dict[str, Any]] = {}
    agents: dict[str, dict[str, Any]] = {}

    if not (root / "AGENTS.md").exists():
        errors.append(f"{root / 'AGENTS.md'}: missing agent entry point")

    legacy = _legacy_files(root)
    if legacy:
        sample = ", ".join(str(p.relative_to(root)) for p in legacy[:4])
        errors.append(
            "protocol v4 removed mutable state/mailbox files; migrate or delete: "
            + sample
        )

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
        if registry.get("protocol_version") != 4:
            errors.append(f"{registry_path}: protocol_version must be 4")
        if registry.get("entrypoint") != "AGENTS.md":
            errors.append(f"{registry_path}: entrypoint must be AGENTS.md")

        defaults = registry.get("defaults") or {}
        lease = defaults.get("ack_lease_hours")
        if not isinstance(lease, int) or lease < 1:
            errors.append(f"{registry_path}: defaults.ack_lease_hours must be >= 1")
        pending_reviews = defaults.get("max_pending_reviews_per_dispatcher")
        if not isinstance(pending_reviews, int) or pending_reviews < 1:
            errors.append(
                f"{registry_path}: defaults.max_pending_reviews_per_dispatcher "
                "must be >= 1"
            )

        github = registry.get("github")
        if not isinstance(github, dict):
            errors.append(f"{registry_path}: github configuration is required")
        else:
            if github.get("task_transport") != "issue":
                errors.append(f"{registry_path}: github.task_transport must be issue")
            for key in ("task_title_prefix", "task_label", "priority_label_prefix"):
                if not github.get(key):
                    errors.append(f"{registry_path}: github.{key} is required")
            status_labels = github.get("status_labels")
            required_statuses = {
                "ready", "claimed", "blocked", "needs_review",
                "accepted", "revise", "rejected"
            }
            if not isinstance(status_labels, dict):
                errors.append(f"{registry_path}: github.status_labels must be a mapping")
            elif set(status_labels) != required_statuses:
                errors.append(
                    f"{registry_path}: github.status_labels must define "
                    + ", ".join(sorted(required_statuses))
                )

        pools = registry.get("pools")
        if not isinstance(pools, dict) or not pools:
            errors.append(f"{registry_path}: pools must be a non-empty mapping")

        bootstrap = registry.get("scheduler_bootstrap")
        if bootstrap is not None:
            if not isinstance(bootstrap, dict):
                errors.append(f"{registry_path}: scheduler_bootstrap must be a mapping")
            else:
                if bootstrap.get("source") not in (None, "pools"):
                    errors.append(
                        f"{registry_path}: scheduler_bootstrap.source must be pools"
                    )
                if bootstrap.get("cadence") not in (None, "hourly"):
                    errors.append(
                        f"{registry_path}: scheduler_bootstrap.cadence must be hourly"
                    )
                template = bootstrap.get("instance_template")
                if template and ("{runtime}" not in str(template) or "{pool}" not in str(template)):
                    errors.append(
                        f"{registry_path}: scheduler_bootstrap.instance_template "
                        "must include {runtime} and {pool}"
                    )
                minutes = bootstrap.get("schedule_minutes") or {}
                if not isinstance(minutes, dict):
                    errors.append(
                        f"{registry_path}: scheduler_bootstrap.schedule_minutes "
                        "must be a mapping"
                    )
                else:
                    pool_names = set(pools) if isinstance(pools, dict) else set()
                    for runtime_name, mapping in minutes.items():
                        if not isinstance(mapping, dict):
                            errors.append(
                                f"{registry_path}: schedule_minutes.{runtime_name} "
                                "must be a mapping"
                            )
                            continue
                        for pool_name, minute in mapping.items():
                            if pool_name not in pool_names:
                                errors.append(
                                    f"{registry_path}: schedule_minutes.{runtime_name} "
                                    f"references unknown pool {pool_name!r}"
                                )
                            if not isinstance(minute, int) or not 0 <= minute <= 59:
                                errors.append(
                                    f"{registry_path}: schedule minute for "
                                    f"{runtime_name}/{pool_name} must be 0..59"
                                )

                orchestrator_schedule = bootstrap.get("orchestrator_schedule") or {}
                if not isinstance(orchestrator_schedule, dict):
                    errors.append(
                        f"{registry_path}: scheduler_bootstrap.orchestrator_schedule "
                        "must be a mapping"
                    )
                else:
                    orchestrator_template = orchestrator_schedule.get("instance_template")
                    if orchestrator_template and "{runtime}" not in str(orchestrator_template):
                        errors.append(
                            f"{registry_path}: orchestrator_schedule.instance_template "
                            "must include {runtime}"
                        )
                    orchestrator_minutes = (
                        orchestrator_schedule.get("schedule_minutes") or {}
                    )
                    if not isinstance(orchestrator_minutes, dict):
                        errors.append(
                            f"{registry_path}: orchestrator_schedule.schedule_minutes "
                            "must be a mapping"
                        )
                    else:
                        for runtime_name, minute in orchestrator_minutes.items():
                            if not isinstance(minute, int) or not 0 <= minute <= 59:
                                errors.append(
                                    f"{registry_path}: orchestrator schedule minute for "
                                    f"{runtime_name} must be 0..59"
                                )

        if not isinstance(registry.get("projects"), list):
            errors.append(f"{registry_path}: projects must be a list")

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
        name = str(name)
        projects[name] = data
        if data.get("schema") != 1:
            errors.append(f"{path}: schema must be 1")
        if data.get("status") not in PROJECT_STATES:
            errors.append(f"{path}: invalid project status {data.get('status')!r}")
        try:
            validate_name(name, "project")
        except ValueError as exc:
            errors.append(f"{path}: {exc}")
        control = data.get("control_plane") or {}
        if control.get("transport") != "github_issue":
            errors.append(f"{path}: control_plane.transport must be github_issue")
        if "mailboxes" in data:
            errors.append(f"{path}: mailboxes were removed in protocol v4")

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
            control = data.get("control_plane") or {}
            if control.get("transport") != "github_issue":
                errors.append(f"{path}: control_plane.transport must be github_issue")
        if "mailbox" in data or "current_task" in data or "current_objective" in data:
            errors.append(f"{path}: mutable mailbox/task fields were removed in protocol v4")

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

    extra = sorted(
        name for name, agent in agents.items()
        if agent.get("project") != "*" and name not in required_workers
    )
    for name in extra:
        warnings.append(f"agent {name}: not listed by its project")

    return ValidationResult(
        registry=registry,
        projects=projects,
        agents=agents,
        errors=errors,
        warnings=warnings,
    )


def infer_auditor(worker_ids: list[str]) -> str | None:
    return next((worker for worker in worker_ids if "audit" in worker), None)


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
    }


def build_orchestrator() -> dict[str, Any]:
    return {
        "schema": 1,
        "agent": "orchestrator",
        "project": "*",
        "role": "project-orchestration",
        "dispatcher_pool": "none",
        "status": "active",
        "project_paths": ["coordination/projects", "coordination/agents"],
    }
