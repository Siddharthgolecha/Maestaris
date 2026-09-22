# Quick start

## AI agent

Start with root `AGENTS.md`.

Read the global registry, project, agent, state index, and current GitHub task Issue before acting.

No CLI invocation is required.

## Repository setup

```bash
python -m pip install -e .

zerion init my-project \
  --workers theory implementation audit \
  --repository owner/repository
```

The generated project uses `github_issue` control-plane transport.

## Create work

Use the Zerion task Issue template in GitHub or create an Issue programmatically with the `[ORCHESTRATOR:v1]` assignment body.

A worker ACKs in the Issue, then opens a linked draft PR for repository changes.

## Validate

```bash
zerion validate
zerion status
```

## Legacy repositories

PR-backed mailboxes remain supported. `zerion init --mailboxes` is a deprecated compatibility path and requires authenticated `gh` shell access.
