#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from urllib import error, parse, request

import yaml

RUNTIME_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = Path(os.environ.get("MAESTARIS_PROJECT_ROOT", str(RUNTIME_ROOT))).resolve()
sys.path.insert(0, str(RUNTIME_ROOT))

from maestaris_orchestration.protocol import (
    desired_managed_labels,
    is_managed_label,
)


LABEL_COLORS = {
    "task": "5319e7",
    "ready": "d4c5f9",
    "claimed": "1d76db",
    "blocked": "d73a4a",
    "needs_review": "fbca04",
    "accepted": "0e8a16",
    "revise": "b60205",
    "rejected": "6e7781",
    "priority": "ededed",
}


class GitHubAPI:
    def __init__(self, repo: str, token: str):
        self.repo = repo
        self.token = token
        self.base = "https://api.github.com"

    def call(self, method: str, path: str, payload=None):
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = request.Request(
            self.base + path,
            data=data,
            method=method,
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "maestaris-orchestration",
                "Content-Type": "application/json",
            },
        )
        try:
            with request.urlopen(req) as response:
                raw = response.read()
                return json.loads(raw) if raw else None
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"GitHub API {method} {path} failed: {exc.code} {body}"
            ) from exc

    def comments(self, issue_number: int) -> list[dict]:
        items: list[dict] = []
        page = 1
        while True:
            batch = self.call(
                "GET",
                f"/repos/{self.repo}/issues/{issue_number}/comments"
                f"?per_page=100&page={page}",
            )
            if not batch:
                break
            items.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return items

    def ensure_label(self, name: str, color: str) -> None:
        encoded = parse.quote(name, safe="")
        try:
            self.call("GET", f"/repos/{self.repo}/labels/{encoded}")
            return
        except RuntimeError as exc:
            if " 404 " not in str(exc):
                raise
        try:
            self.call(
                "POST",
                f"/repos/{self.repo}/labels",
                {"name": name, "color": color},
            )
        except RuntimeError as exc:
            if " 422 " not in str(exc):
                raise


def label_color(label: str, github: dict) -> str:
    if label == github["task_label"]:
        return LABEL_COLORS["task"]

    for state, state_label in github["status_labels"].items():
        if label == state_label:
            return LABEL_COLORS.get(state, "ededed")

    if label.startswith(str(github["priority_label_prefix"])):
        priority = label[len(str(github["priority_label_prefix"])) :].upper()
        if priority == "P0":
            return "b60205"
        if priority == "P1":
            return "d93f0b"
        return LABEL_COLORS["priority"]

    return "ededed"


def main() -> int:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    repo = os.environ.get("GITHUB_REPOSITORY")
    token = os.environ.get("GITHUB_TOKEN")
    explicit_issue_number = os.environ.get("MAESTARIS_ISSUE_NUMBER")

    if not repo or not token:
        print("GitHub repository/token is unavailable; skipping sync.")
        return 0

    event = (
        json.loads(Path(event_path).read_text(encoding="utf-8"))
        if event_path and Path(event_path).exists()
        else {}
    )
    issue = event.get("issue") or {}
    api = GitHubAPI(repo, token)
    if not issue and explicit_issue_number:
        issue = api.call("GET", f"/repos/{repo}/issues/{int(explicit_issue_number)}") or {}
    if not issue:
        print("No Issue context is available; skipping sync.")
        return 0

    title = issue.get("title") or ""
    body = issue.get("body") or ""

    registry = yaml.safe_load(
        (PROJECT_ROOT / "coordination" / "maestaris.yaml").read_text()
    )
    github = registry["github"]
    prefix = str(github["task_title_prefix"])

    if not title.startswith(prefix):
        print("Not a Maestaris task Issue; skipping sync.")
        return 0

    number = int(issue["number"])
    comments = api.comments(number)
    comment_bodies = [str(item.get("body") or "") for item in comments]

    desired = desired_managed_labels(body, comment_bodies, github)
    current = {
        item["name"] if isinstance(item, dict) else str(item)
        for item in (issue.get("labels") or [])
    }
    preserved = {label for label in current if not is_managed_label(label, github)}
    final_labels = preserved | desired

    for label in desired:
        api.ensure_label(label, label_color(label, github))

    api.call(
        "PUT",
        f"/repos/{repo}/issues/{number}/labels",
        {"labels": sorted(final_labels)},
    )

    print("Maestaris labels synchronized: " + ", ".join(sorted(desired)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
