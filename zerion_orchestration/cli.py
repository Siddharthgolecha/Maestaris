from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Sequence

from . import __version__
from .audit import audit_snapshot, reconcile_labels
from .core import (
    build_agent,
    build_orchestrator,
    build_project,
    build_registry,
    dump_yaml,
    ensure_agents_entrypoint,
    ensure_layout,
    infer_repository_from_git,
    load_yaml,
    validate_name,
    validate_repository,
)
from .doctor import capability_report, render_report


def _root(value: str) -> Path:
    return Path(value).expanduser().resolve()


def command_init(args: argparse.Namespace) -> int:
    root = _root(args.root)
    ensure_layout(root)
    created_agents_md = ensure_agents_entrypoint(root)

    validate_name(args.project, "project")
    for role in args.workers:
        validate_name(role, "worker role")

    registry_path = root / "coordination" / "zerion.yaml"
    registry = load_yaml(registry_path) if registry_path.exists() else build_registry()

    if registry.get("protocol_version") != 4:
        print(
            "existing Zerion registry is not protocol v4; migrate before init",
            file=sys.stderr,
        )
        return 2

    project_path = root / "coordination" / "projects" / f"{args.project}.yaml"
    if project_path.exists() and not args.force:
        print(f"project already exists: {project_path}", file=sys.stderr)
        return 2

    workers = [f"{args.project}-{role}" for role in args.workers]
    for worker in workers:
        path = root / "coordination" / "agents" / f"{worker}.yaml"
        if path.exists() and not args.force:
            print(f"agent already exists: {path}", file=sys.stderr)
            return 2

    repository = args.repository or infer_repository_from_git(root)
    title = args.title or args.project.replace("-", " ").title()

    orchestrator_path = root / "coordination" / "agents" / "orchestrator.yaml"
    if not orchestrator_path.exists():
        dump_yaml(orchestrator_path, build_orchestrator())

    dump_yaml(
        project_path,
        build_project(args.project, title, repository, args.runtime, workers),
    )

    for index, (worker, role) in enumerate(zip(workers, args.workers)):
        pool = "A" if index % 2 == 0 else "B"
        path = root / "coordination" / "agents" / f"{worker}.yaml"
        dump_yaml(path, build_agent(worker, args.project, role, pool))

    registered = list(registry.get("projects") or [])
    if args.project not in registered:
        registered.append(args.project)
    registry["projects"] = registered
    dump_yaml(registry_path, registry)

    print(f"Initialized Zerion project '{args.project}' with {len(workers)} worker(s).")
    if created_agents_md:
        print("Created root AGENTS.md entry point.")
    print(f"Project registry: {project_path.relative_to(root)}")
    print("Live task state: GitHub Issues/comments/PRs (no mutable state YAML).")

    return command_validate(argparse.Namespace(root=str(root), quiet=True))


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
            f"{len(result.projects)} project(s), {len(result.agents)} agent(s)"
        )
    return 0


def command_status(args: argparse.Namespace) -> int:
    root = _root(args.root)
    result = validate_repository(root)

    if args.json:
        print(
            json.dumps(
                {
                    "ok": result.ok,
                    "errors": result.errors,
                    "warnings": result.warnings,
                    "registry": result.registry,
                    "projects": result.projects,
                    "agents": result.agents,
                    "live_state": "github",
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0 if result.ok else 1

    print("Zerion live task state is in GitHub Issues/PRs, not local YAML.")
    print("PROJECT                  STATUS      WORKERS  REPOSITORY")
    print("-----------------------  ----------  -------  ------------------------------")
    for name, project in sorted(result.projects.items()):
        workers = len(project.get("active_workers") or [])
        print(
            f"{name[:23]:23}  {str(project.get('status'))[:10]:10}  "
            f"{workers:>7}  {project.get('repository', '-')}"
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


def command_doctor(args: argparse.Namespace) -> int:
    report = capability_report(_root(args.root))
    print(render_report(report, as_json=args.json))
    return 0


def command_audit(args: argparse.Namespace) -> int:
    root = _root(args.root)
    registry = load_yaml(root / "coordination" / "zerion.yaml")
    snapshot = json.loads(Path(args.input).read_text(encoding="utf-8"))
    report = audit_snapshot(snapshot, registry["github"])
    if args.fix:
        repairs = []
        for task in snapshot.get("tasks", []):
            desired = sorted(
                reconcile_labels(
                    str(task.get("body", "")),
                    task.get("comments", []),
                    task.get("labels", []),
                    registry["github"],
                )
            )
            if desired != sorted(task.get("labels", [])):
                repairs.append(
                    {"issue": task.get("number"), "kind": "labels", "desired": desired}
                )
        report["repairs"] = repairs
        report["fix_mode"] = "dry-run" if args.dry_run else "plan-only"
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        findings = [
            (item["issue"], finding)
            for item in report["tasks"]
            for finding in item["findings"]
        ]
        globals_ = report["global_findings"]
        print(f"Zerion audit: {len(findings) + len(globals_)} finding(s)")
        for issue, finding in findings:
            print(
                f"- issue #{issue}: {finding['severity']} "
                f"{finding['code']}: {finding['message']}"
            )
        for finding in globals_:
            print(
                f"- repository: {finding['severity']} "
                f"{finding['code']}: {finding['message']}"
            )
        if args.fix:
            print(
                f"Safe derived repair plan: {len(report.get('repairs', []))} "
                "label update(s); canonical history untouched"
            )
    has_error = any(
        finding["severity"] == "error"
        for item in report["tasks"]
        for finding in item["findings"]
    ) or any(
        finding["severity"] == "error" for finding in report["global_findings"]
    )
    return 1 if has_error else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="zerion",
        description="Static setup and validation for GitHub-native Zerion projects.",
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
    init.add_argument(
        "--repository",
        help="GitHub owner/repository; inferred from local git remote when possible",
    )
    init.add_argument("--runtime", default="runtime-defined")
    init.add_argument("--force", action="store_true")
    init.set_defaults(func=command_init)

    validate = sub.add_parser("validate", help="validate static Zerion configuration")
    validate.set_defaults(func=command_validate)

    status = sub.add_parser("status", help="show static project registration")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=command_status)

    doctor = sub.add_parser("doctor", help="report optional runtime capabilities")
    doctor.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    doctor.set_defaults(func=command_doctor)

    audit = sub.add_parser(
        "audit",
        help="audit a GitHub-derived project snapshot without rewriting canonical history",
    )
    audit.add_argument(
        "--input",
        required=True,
        help="JSON snapshot of tasks/topology/optional Project state",
    )
    audit.add_argument("--json", action="store_true")
    audit.add_argument(
        "--fix", action="store_true", help="emit a safe derived-state repair plan only"
    )
    audit.add_argument(
        "--dry-run", action="store_true", help="mark repair output explicitly as dry-run"
    )
    audit.set_defaults(func=command_audit)

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
