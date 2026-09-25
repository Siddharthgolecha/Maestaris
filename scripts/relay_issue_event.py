#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from maestaris_orchestration.protocol import protocol_fields
from maestaris_orchestration.relay import comment_has_event_id, parse_relay_request


API = "https://api.github.com"


def api(method: str, path: str, token: str, payload=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = Request(
        API + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "maestaris-protocol-relay",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode() or "{}")
    except HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"GitHub API {method} {path} failed: {exc.code} {detail}") from exc


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: relay_issue_event.py <request.json>")

    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo or "/" not in repo:
        raise RuntimeError("GITHUB_TOKEN and GITHUB_REPOSITORY are required")

    payload = parse_relay_request(Path(sys.argv[1]).read_text())
    issue_number = payload["issue_number"]
    event_id = payload["event_id"]
    body = payload["body"]

    issue = api("GET", f"/repos/{repo}/issues/{issue_number}", token)
    if not str(issue.get("title") or "").startswith("[Maestaris task]"):
        raise RuntimeError("relay target is not a Maestaris task Issue")

    task_id = protocol_fields(str(issue.get("body") or "")).get("task_id")
    event_task_id = protocol_fields(body).get("task_id")
    if not task_id or event_task_id != task_id:
        raise RuntimeError("relay event task_id does not match target Issue")

    page = 1
    while True:
        comments = api("GET", f"/repos/{repo}/issues/{issue_number}/comments?per_page=100&page={page}", token)
        if any(comment_has_event_id(str(c.get("body") or ""), event_id) for c in comments):
            print(f"relay event {event_id} already present; skipping")
            return 0
        if len(comments) < 100:
            break
        page += 1

    api("POST", f"/repos/{repo}/issues/{issue_number}/comments", token, {"body": body})
    print(f"relayed {event_id} to issue #{issue_number}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
