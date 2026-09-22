from __future__ import annotations

import base64
import json
from pathlib import Path
import shutil
import subprocess
from typing import Any

from .core import dump_yaml, load_yaml


class GitHubCLIError(RuntimeError):
    pass


def _run(args: list[str], cwd: Path) -> str:
    try:
        result = subprocess.run(
            args,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        raise GitHubCLIError(str(exc)) from exc
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip()
        raise GitHubCLIError(f"{' '.join(args)} failed: {detail}")
    return result.stdout.strip()


def require_gh(root: Path) -> None:
    if shutil.which("gh") is None:
        raise GitHubCLIError(
            "GitHub CLI (gh) is required for mailbox creation. "
            "Install it and run 'gh auth login'."
        )
    _run(["gh", "auth", "status"], root)


def infer_repository(root: Path) -> str:
    require_gh(root)
    return _run(
        ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
        root,
    )


def default_branch(root: Path, repository: str) -> str:
    return _run(
        [
            "gh", "repo", "view", repository,
            "--json", "defaultBranchRef",
            "-q", ".defaultBranchRef.name",
        ],
        root,
    )


def _api_json(root: Path, args: list[str]) -> Any:
    out = _run(["gh", "api", *args], root)
    return json.loads(out) if out else None


def create_mailboxes(
    root: Path,
    project_name: str,
    *,
    repository: str | None = None,
    base: str | None = None,
) -> dict[str, int]:
    require_gh(root)
    project_path = root / "coordination" / "projects" / f"{project_name}.yaml"
    if not project_path.exists():
        raise GitHubCLIError(f"project not found: {project_path}")

    project = load_yaml(project_path)
    repo = repository or project.get("repository")
    if not repo or repo == "owner/repository":
        repo = infer_repository(root)
        project["repository"] = repo

    base_branch = base or default_branch(root, str(repo))
    ref = _api_json(root, [f"repos/{repo}/git/ref/heads/{base_branch}"])
    base_sha = ref["object"]["sha"]

    created: dict[str, int] = {}
    mailboxes = project.setdefault("mailboxes", {})

    for worker in project.get("active_workers") or []:
        if mailboxes.get(worker):
            continue

        branch = f"zerion/mailbox/{project_name}/{worker}"
        marker = f"coordination/mailboxes/{project_name}/{worker}.md"
        encoded = base64.b64encode(
            (
                f"# Zerion mailbox: {worker}\n\n"
                f"Project: {project_name}\n\n"
                "This draft PR is a control-plane mailbox. "
                "Do not commit substantive project work to this branch.\n"
            ).encode("utf-8")
        ).decode("ascii")

        _run(
            [
                "gh", "api", "--method", "POST",
                f"repos/{repo}/git/refs",
                "-f", f"ref=refs/heads/{branch}",
                "-f", f"sha={base_sha}",
            ],
            root,
        )
        _run(
            [
                "gh", "api", "--method", "PUT",
                f"repos/{repo}/contents/{marker}",
                "-f", f"message=Create Zerion mailbox for {worker}",
                "-f", f"content={encoded}",
                "-f", f"branch={branch}",
            ],
            root,
        )
        url = _run(
            [
                "gh", "pr", "create",
                "--repo", str(repo),
                "--base", base_branch,
                "--head", branch,
                "--draft",
                "--title", f"[Zerion mailbox] {worker}",
                "--body",
                (
                    f"Permanent Zerion control-plane mailbox for {worker} "
                    f"in project {project_name}.\n\n"
                    "Do not merge this PR. Substantive work belongs in task PRs."
                ),
            ],
            root,
        )
        number = int(
            _run(
                ["gh", "pr", "view", url, "--repo", str(repo), "--json", "number", "-q", ".number"],
                root,
            )
        )
        mailboxes[worker] = number
        created[worker] = number

        agent_path = root / "coordination" / "agents" / f"{worker}.yaml"
        if agent_path.exists():
            agent = load_yaml(agent_path)
            agent.setdefault("mailbox", {})["pr"] = number
            dump_yaml(agent_path, agent)

    dump_yaml(project_path, project)
    return created


def commit_setup(root: Path, message: str) -> None:
    if not _run(["git", "status", "--porcelain"], root):
        return
    _run(["git", "add", "coordination"], root)
    if not _run(["git", "diff", "--cached", "--name-only"], root):
        return
    _run(["git", "commit", "-m", message], root)
    _run(["git", "push"], root)
