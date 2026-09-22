#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from urllib import error, request

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from zerion_orchestration.project_sync import project_field_values


GRAPHQL_URL = "https://api.github.com/graphql"


class GraphQL:
    def __init__(self, token: str):
        self.token = token

    def call(self, query: str, variables: dict) -> dict:
        payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        req = request.Request(
            GRAPHQL_URL,
            data=payload,
            method="POST",
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": f"Bearer {self.token}",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "zerion-orchestration",
                "Content-Type": "application/json",
            },
        )
        try:
            with request.urlopen(req) as response:
                data = json.loads(response.read())
        except error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"GitHub GraphQL failed: {exc.code} {body}") from exc

        if data.get("errors"):
            raise RuntimeError("GitHub GraphQL errors: " + json.dumps(data["errors"]))
        return data["data"]


def project_snapshot(api: GraphQL, project_id: str) -> dict:
    query = """
    query($project: ID!) {
      node(id: $project) {
        ... on ProjectV2 {
          id
          fields(first: 100) {
            nodes {
              __typename
              ... on ProjectV2Field { id name dataType }
              ... on ProjectV2SingleSelectField {
                id
                name
                options { id name }
              }
            }
          }
          items(first: 100) {
            nodes {
              id
              content {
                ... on Issue { id }
              }
            }
          }
        }
      }
    }
    """
    return api.call(query, {"project": project_id})["node"]


def ensure_item(api: GraphQL, project_id: str, issue_node_id: str, snapshot: dict) -> str:
    for item in (snapshot.get("items") or {}).get("nodes") or []:
        content = item.get("content") or {}
        if content.get("id") == issue_node_id:
            return item["id"]

    mutation = """
    mutation($project: ID!, $content: ID!) {
      addProjectV2ItemById(input: {projectId: $project, contentId: $content}) {
        item { id }
      }
    }
    """
    data = api.call(mutation, {"project": project_id, "content": issue_node_id})
    return data["addProjectV2ItemById"]["item"]["id"]


def update_field(
    api: GraphQL,
    project_id: str,
    item_id: str,
    field: dict,
    value: str,
) -> None:
    typename = field.get("__typename")
    if typename == "ProjectV2SingleSelectField":
        option = next(
            (option for option in field.get("options") or [] if option.get("name") == value),
            None,
        )
        if not option:
            print(
                f"Project field {field.get('name')!r} has no option {value!r}; skipping."
            )
            return
        encoded = {"singleSelectOptionId": option["id"]}
    elif typename == "ProjectV2Field":
        encoded = {"text": value}
    else:
        print(f"Unsupported Project field type for {field.get('name')!r}; skipping.")
        return

    mutation = """
    mutation($project: ID!, $item: ID!, $field: ID!, $value: ProjectV2FieldValue!) {
      updateProjectV2ItemFieldValue(
        input: {projectId: $project, itemId: $item, fieldId: $field, value: $value}
      ) {
        projectV2Item { id }
      }
    }
    """
    api.call(
        mutation,
        {
            "project": project_id,
            "item": item_id,
            "field": field["id"],
            "value": encoded,
        },
    )


def main() -> int:
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("GITHUB_EVENT_PATH is unavailable; skipping Project sync.")
        return 0

    registry = yaml.safe_load((ROOT / "coordination" / "zerion.yaml").read_text())
    project_cfg = ((registry.get("github") or {}).get("projects") or {})
    field_sync = project_cfg.get("field_sync") or {}

    if not field_sync.get("enabled"):
        print("Zerion Project field sync is disabled.")
        return 0

    project_id_env = str(field_sync.get("project_id_env", "ZERION_PROJECT_ID"))
    token_env = str(field_sync.get("token_env", "ZERION_PROJECT_TOKEN"))
    project_id = os.environ.get(project_id_env)
    token = os.environ.get(token_env)

    if not project_id or not token:
        print(
            f"Project sync configured but {project_id_env}/{token_env} is missing; "
            "labels remain the portable dashboard fallback."
        )
        return 0

    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    issue = event.get("issue") or {}
    issue_node_id = issue.get("node_id")
    if not issue_node_id:
        print("No Issue node ID in event; skipping Project sync.")
        return 0

    title = issue.get("title") or ""
    prefix = str((registry.get("github") or {}).get("task_title_prefix", "[Zerion task]"))
    if not title.startswith(prefix):
        print("Not a Zerion task Issue; skipping Project sync.")
        return 0

    repo = os.environ.get("GITHUB_REPOSITORY")
    github_token = os.environ.get("GITHUB_TOKEN")
    if not repo or not github_token:
        print("Repository/GITHUB_TOKEN unavailable; skipping Project sync.")
        return 0

    # Read comments with the repository token. Project mutation uses the separate
    # token because user/org Projects may require permissions beyond GITHUB_TOKEN.
    from sync_github_issue import GitHubAPI

    comments = GitHubAPI(repo, github_token).comments(int(issue["number"]))
    comment_bodies = [str(item.get("body") or "") for item in comments]

    values = project_field_values(issue.get("body") or "", comment_bodies, field_sync)
    api = GraphQL(token)
    snapshot = project_snapshot(api, project_id)
    item_id = ensure_item(api, project_id, issue_node_id, snapshot)

    field_names = field_sync.get("fields") or {}
    fields = {
        field.get("name"): field
        for field in (snapshot.get("fields") or {}).get("nodes") or []
        if field and field.get("name")
    }

    for logical_name, value in values.items():
        configured_name = field_names.get(logical_name)
        if not configured_name:
            continue
        field = fields.get(configured_name)
        if not field:
            print(
                f"Project field {configured_name!r} is not present; "
                f"skipping {logical_name}."
            )
            continue
        update_field(api, project_id, item_id, field, value)

    print("Zerion Project fields synchronized where configured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
