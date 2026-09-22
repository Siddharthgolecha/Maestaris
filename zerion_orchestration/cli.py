from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from . import __version__
from .core import (
    build_agent,
    build_orchestrator,
    build_project,
    build_registry,
    build_state,
    dump_yaml,
    ensure_agents_entrypoint,
    ensure_layout,
    load_yaml,
    validate_name,
    validate_repository,
)
from .github import GitHubCLIError, commit_setup, create_mailboxes, infer_repository


def _root(value: str) -> Path:
    return Path(value).expanduser().resolve()


def _maybe_repo(root: Path, requested: str | None) -> str:
    if requested:
        return requested
    try:
        return infer_repository(root)
    except Exception:
        return "owner/repository"


def _enable_legacy_mailboxes(root: Path, project_name: str, workers: list[str]) -> None:
    project_path = root / "coordination" / "projects" / f"{project_name}.yaml"
    project = load_yaml(project_path)
    project["control_plane"] = {"transport": "legacy_pull_request_mailbox"}
    project["mailboxes"] = {worker: None for worker in workers}
    dump_yaml(project_path, project)

    for worker in workers:
        agent_path = root / "coordination" / "agents" / f"{worker}.yaml"
        agent = load_yaml(agent_path)
        agent["control_plane"] = {"transport": "legacy_pull_request_mailbox"}
        agent["mailbox"] = {"transport": "pull_request", "pr": None}
        dump_yaml(agent_path, agent)

        state_path = root / "coordination" / "state" / f"{worker}.yaml"
        state = load_yaml(state_path)
        state["mailbox"] = {"pr": None}
        dump_yaml(state_path, state)


def command_init(args: argparse.Namespace) -> int:
    root = _root(args.root)
    ensure_layout(root)
    created_agents_md = ensure_agents_entrypoint(root)
    validate_name(args.project, "project")
    for role in args.workers:
        validate_name(role, "worker role")

    registry_path = root / "coordination" / "zerion.yaml"
    registry = load_yaml(registry_path) if registry_path.exists() else build_registry()

    project_path = root / "coordination" / "projects" / f"{args.project}.yaml"
    if project_path.exists() and not args.force:
        print(f"project already exists: {project_path}", file=sys.stderr)
        return 2

    workers = [f"{args.project}-{role}" for role in args.workers]
    for worker in workers:
        agent_path = root / "coordination" / "agents" / f"{worker}.yaml"
        state_path = root / "coordination" / "state" / f"{worker}.yaml"
        if not args.force and (agent_path.exists() or state_path.exists()):
            occupied = agent_path if agent_path.exists() else state_path
            print(f"worker already exists: {occupied}", file=sys.stderr)
            return 2

    repository = _maybe_repo(root, args.repository)
    title = args.title or args.project.replace("-", " ").title()

    orchestrator_path = root / "coordination" / "agents" / "orchestrator.yaml"
    if not orchestrator_path.exists():
        dump_yaml(orchestrator_path, build_orchestrator())

    dump_yaml(
        project_path,
        build_project(args.project, title, repository, args.runtime, workers),
    )

    lease_hours = int((registry.get("defaults") or {}).get("ack_lease_hours", 3))
    for index, (worker, role) in enumerate(zip(workers, args.workers)):
        agent_path = root / "coordination" / "agents" / f"{worker}.yaml"
        state_path = root / "coordination" / "state" / f"{worker}.yaml"
        pool = "A" if index % 2 == 0 else "B"
        dump_yaml(agent_path, build_agent(worker, args.project, role, pool))
        dump_yaml(state_path, build_state(worker, args.project, lease_hours))

    registered = list(registry.get("projects") or [])
    if args.project not in registered:
        registered.append(args.project)
    registry["projects"] = registered
    dump_yaml(registry_path, registry)

    print(f"Initialized Zerion project '{args.project}' with {len(workers)} worker(s).")
    if created_agents_md:
        print("Created root AGENTS.md entry point.")
    print(f"Project registry: {project_path.relative_to(root)}")
    print("Control plane: GitHub Issues (preferred native transport).")

    if args.mailboxes:
        print(
            "warning: --mailboxes enables deprecated PR-backed mailbox transport",
            file=sys.stderr,
        )
        _enable_legacy_mailboxes(root, args.project, workers)
        try:
            created = create_mailboxes(root, args.project, repository=repository)
        except GitHubCLIError as exc:
            print(f"legacy mailbox bootstrap failed: {exc}", file=sys.stderr)
            return 1
        for worker, number in created.items():
            print(f"Legacy mailbox PR #{number}: {worker}")
        if args.commit:
            try:
                commit_setup(root, f"Register Zerion project {args.project}")
            except GitHubCLIError as exc:
                print(f"commit/push failed: {exc}", file=sys.stderr)
                return 1
    elif args.commit:
        print("--commit has effect only together with --mailboxes", file=sys.stderr)
        return 2

    return command_validate(argparse.Namespace(root=str(root), quiet=True))


def command_mailboxes_create(args: argparse.Namespace) -> int:
    root = _root(args.root)
    try:
        created = create_mailboxes(
            root,
            args.project,
            repository=args.repository,
            base=args.base,
        )
        if args.commit:
            commit_setup(root, f"Register legacy Zerion mailboxes for {args.project}")
    except GitHubCLIError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not created:
        print("No legacy mailboxes created; all workers already have mailbox PRs.")
    else:
        for worker, number in created.items():
            print(f"Created legacy mailbox PR #{number}: {worker}")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    root = _root(args.root)
    result = validate_repository(root)
    if result.errors:
        print("Zerion configuration validation FAILED", file=sys.stderr)
        for error in result.errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    if result.warnings and not getattr(args, "quiet", False):
        print("Zerion configuration warnings:", file=sys.stderr)
        for warning in result.warnings:
            print(f"- {warning}", file=sys.stderr)

    if not getattr(args, "quiet", False):
        print(
            f"Zerion configuration validation OK: "
            f"{len(result.projects)} project(s), {len(result.agents)} agent(s), "
            f"{len(result.states)} worker state index(es)"
        )
    return 0


def _project_control_stats(project_name: str, project: dict, states: dict) -> tuple[str, int, int]:
    workers = project.get("active_workers") or []
    control = project.get("control_plane") or {}
    transport = control.get("transport")
    if transport == "github_issue":
        configured = sum(
            1
            for worker in workers
            if ((states.get(worker) or {}).get("task") or {}).get("issue")
        )
        return "issues", configured, len(workers)

    mailboxes = project.get("mailboxes") or {}
    configured = sum(1 for worker in workers if mailboxes.get(worker))
    return "legacy-pr", configured, len(workers)


def command_status(args: argparse.Namespace) -> int:
    root = _root(args.root)
    result = validate_repository(root)
    if args.json:
        payload = {
            "ok": result.ok,
            "errors": result.errors,
            "warnings": result.warnings,
            "registry": result.registry,
            "projects": result.projects,
            "agents": result.agents,
            "states": result.states,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if result.ok else 1

    if not result.projects:
        print("No Zerion projects registered.")
        return 1 if result.errors else 0

    print("PROJECT                  STATUS      CONTROL    ACTIVE  WORKERS")
    print("-----------------------  ----------  ---------  ------  ------------------------------")
    for name, project in sorted(result.projects.items()):
        control, configured, total = _project_control_stats(name, project, result.states)
        workers = ", ".join(project.get("active_workers") or []) or "-"
        print(
            f"{name[:23]:23}  {str(project.get('status'))[:10]:10}  "
            f"{control[:9]:9}  {configured:>2}/{total:<3}  {workers}"
        )

    if result.warnings:
        print("\nWarnings:")
        for warning in result.warnings:
            print(f"- {warning}")

    if result.errors:
        print("\nValidation issues:")
        for error in result.errors:
            print(f"- {error}")
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zerion",
        description="GitHub-backed orchestration for persistent AI workers.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--root", default=".", help="repository root (default: current directory)")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="register a new Zerion project")
    init.add_argument("project")
    init.add_argument("--title")
    init.add_argument(
        "--workers",
        nargs="+",
        default=["theory", "implementation", "audit"],
        help="worker roles; IDs are namespaced as project-role",
    )
    init.add_argument("--repository", help="GitHub owner/repository; inferred with gh when possible")
    init.add_argument("--runtime", default="runtime-defined")
    init.add_argument(
        "--mailboxes",
        action="store_true",
        help="DEPRECATED: use legacy draft-PR mailboxes instead of GitHub task Issues",
    )
    init.add_argument(
        "--commit",
        action="store_true",
        help="with --mailboxes, commit legacy coordination changes and push",
    )
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=command_init)

    validate = sub.add_parser("validate", help="validate Zerion configuration")
    validate.set_defaults(func=command_validate)

    status = sub.add_parser("status", help="show projects, workers, and control-plane refs")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=command_status)

    mailboxes = sub.add_parser("mailboxes", help="manage deprecated PR-backed mailboxes")
    mailbox_sub = mailboxes.add_subparsers(dest="mailbox_command", required=True)
    create = mailbox_sub.add_parser("create", help="create missing legacy draft mailbox PRs")
    create.add_argument("project")
    create.add_argument("--repository")
    create.add_argument("--base")
    create.add_argument("--commit", action="store_true", help="commit and push registry updates")
    create.set_defaults(func=command_mailboxes_create)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
