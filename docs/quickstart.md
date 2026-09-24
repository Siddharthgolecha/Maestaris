# Quick start

## 1. Put Maestaris in the repository

Use this repository as a template or copy its `AGENTS.md`, `coordination/`, `prompts/`, and relevant `.github/` files.

Optional helper:

```bash
python -m pip install -e .
maestaris init my-project \
  --workers theory implementation audit \
  --repository owner/repository
maestaris validate
```

The CLI creates static configuration only.

## 2. Create ChatGPT roles

A common topology is:

- one orchestrator chat;
- one or two scheduled worker-pool chats;
- specialist identities defined in `coordination/agents/`.

The same scheduled pool can service multiple specialist identities.

## 3. Point chats at GitHub

Tell a fresh conversation to read `AGENTS.md` and operate Maestaris on the repository.

Workers discover live work from GitHub Issues rather than chat memory.

## 4. Create tasks

Create a structured `[Maestaris task]` Issue.

The worker ACKs in a comment, performs the bounded work, links a draft PR when appropriate, and posts its terminal result on the Issue.

## 5. Let Actions handle mechanics

The shipped workflow validates protocol records and derives labels from the Issue history.

## 6. Optional GitHub Project

Create a Project and configure Auto-add with:

```text
is:issue label:"maestaris:task"
```

Use labels for Blocked, Needs review, Claimed, and Priority views.

See `docs/github-projects.md`.
