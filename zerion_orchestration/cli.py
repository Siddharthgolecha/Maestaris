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
    dump_yaml,
    ensure_layout,
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


def command_init(args: argparse.Namespace) -> int:
    root = _root(args.root)
    ensure_layout(root)
    validate_name(args.project, "project")
    for role in args.workers:
        validate_name(role, "worker role")

    project_path = root / "coordination" / "projects" / f"{args.project}.yaml"
    if project_path.exists() and not args.force:
        print(f"project already exists: {project_path}", file=sys.stderr)
        return 2

    workers = [f"{args.project}-{role}" for role in args.workers]
    repository = _maybe_repo(root, args.repository)
    title = args.title or args.project.replace("-", " ").title()

    orchestrator_path = root / "coordination" / "agents" / "orchestrator.yaml"
    if not orchestrator_path.exists():
        dump_yaml(orchestrator_path, build_orchestrator())

    dump_yaml(
        project_path,
        build_project(args.project, title, repository, args.runtime, workers),
    )

    for index, (worker, role) in enumerate(zip(workers, args.workers)):
        agent_path = root / "coordination" / "agents" / f"{worker}.yaml"
        if agent_path.exists() and not args.force:
            print(f"agent already exists: {agent_path}", file=sys.stderr)
            return 2
        pool = "A" if index % 2 == 0 else "B"
        dump_yaml(agent_path, build_agent(worker, args.project, role, pool))

    print(f"Initialized Zerion project '{args.project}' with {len(workers)} worker(s).")
    print(f"Project registry: {project_path.relative_to(root)}")

    if args.mailboxes:
        try:
            created = create_mailboxes(root, args.project, repository=repository)
        except GitHubCLIError as exc:
            print(f"mailbox bootstrap failed: {exc}", file=sys.stderr)
            return 1
        for worker, number in created.items():
            print(f"Mailbox #{number}: {worker}")
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
            commit_setup(root, f"Register Zerion mailboxes for {args.project}")
    except GitHubCLIError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if not created:
        print("No mailboxes created; all active workers already have mailbox PRs.")
    else:
        for worker, number in created.items():
            print(f"Created mailbox #{number}: {worker}")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    root = _root(args.root)
    result = validate_repository(root)
    if result.errors:
        print("Zerion configuration validation FAILED", file=sys.stderr)
        for error in result.errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    if not getattr(args, "quiet", False):
        print(
            f"Zerion configuration validation OK: "
            f"{len(result.projects)} project(s), {len(result.agents)} agent(s)"
        )
    return 0


def _mailbox_count(project: dict) -> tuple[int, int]:
    workers = project.get("active_workers") or []
    mailboxes = project.get("mailboxes") or {}
    configured = sum(1 for worker in workers if mailboxes.get(worker))
    return configured, len(workers)


def command_status(args: argparse.Namespace) -> int:
    root = _root(args.root)
    result = validate_repository(root)
    if args.json:
        payload = {
            "ok": result.ok,
            "errors": result.errors,
            "projects": result.projects,
            "agents": result.agents,
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if result.ok else 1

    if not result.projects:
        print("No Zerion projects registered.")
        return 1 if result.errors else 0

    print("PROJECT                  STATUS      MAILBOXES  WORKERS")
    print("-----------------------  ----------  ---------  ------------------------------")
    for name, project in sorted(result.projects.items()):
        configured, total = _mailbox_count(project)
        workers = ", ".join(project.get("active_workers") or []) or "-"
        print(
            f"{name[:23]:23}  {str(project.get('status'))[:10]:10}  "
            f"{configured:>2}/{total:<6}  {workers}"
        )

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
    init.add_argument("--mailboxes", action="store_true", help="create draft mailbox PRs with gh")
    init.add_argument(
        "--commit",
        action="store_true",
        help="with --mailboxes, commit coordination changes and push",
    )
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=command_init)

    validate = sub.add_parser("validate", help="validate Zerion configuration")
    validate.set_defaults(func=command_validate)

    status = sub.add_parser("status", help="show projects, workers, and mailbox coverage")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=command_status)

    mailboxes = sub.add_parser("mailboxes", help="manage control-plane mailbox PRs")
    mailbox_sub = mailboxes.add_subparsers(dest="mailbox_command", required=True)
    create = mailbox_sub.add_parser("create", help="create missing draft mailbox PRs")
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
