# Quick start

## For an AI agent

Start with the repository's root `AGENTS.md`.

Do not begin by trusting chat history. Follow its bootstrap sequence to read:

1. `coordination/zerion.yaml`;
2. the relevant project;
3. agent and worker-state configuration;
4. the mailbox PR;
5. canonical project files;
6. actual task evidence.

No CLI invocation is required for agent operation.

## For repository setup

Install Zerion locally:

```bash
python -m pip install -e .
```

Initialize a project:

```bash
zerion init my-project \
  --workers theory implementation audit \
  --repository owner/repository
```

This registers the project globally, creates namespaced agent entries, and creates one current-state index per worker.

## Optional mailbox creation

With authenticated GitHub CLI:

```bash
zerion mailboxes create my-project --commit
```

This creates one long-lived draft mailbox PR per worker and synchronizes the PR number across project, agent, and state registries.

Do not merge mailbox PRs and do not put substantive work on mailbox branches.

## Assign a bounded task

Post an `[ORCHESTRATOR:v1]` message using the assignment template and synchronize the worker state index to `assigned`.

## Run a worker

A worker pool uses the state index to find candidates, verifies the real mailbox state, posts ACK, updates state to `claimed`, reads canonical paths, creates a task PR, performs and verifies work, then posts a terminal result and synchronizes state.

## Review

The orchestrator inspects the actual task PR, commit, CI, proof, experiment, or artifact before accepting the result.

## Validate

```bash
zerion validate
```

Validation checks the global registry, projects, agents, worker-state coverage, pool references, and mailbox-reference consistency.
