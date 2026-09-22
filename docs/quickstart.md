# Quick start

## 1. Add Zerion to a project

Use this repository as a template, fork it, or copy the coordination layer into an existing repository.

## 2. Register a project

Copy `coordination/templates/PROJECT_TEMPLATE.yaml` into `coordination/projects/<project>.yaml` and edit the canonical paths and workers.

## 3. Register workers

Copy `coordination/templates/AGENT_TEMPLATE.yaml` once per specialist. Assign each worker to a dispatcher pool.

## 4. Create mailbox PRs

Create one tiny, long-lived draft PR per active worker. The branch should contain only its mailbox marker file.

Do not commit substantive work to mailbox branches.

## 5. Assign a bounded task

Post an `[ORCHESTRATOR:v1]` message using the assignment template.

## 6. Run a worker

A worker pool discovers the assignment, posts ACK, reads canonical state, creates a task branch, performs work, verifies it, opens or updates a task PR, and posts a terminal result.

## 7. Review

The orchestrator inspects the actual commit, PR, CI, proof, experiment, or artifact before accepting the result.

## 8. Validate configuration

```bash
python -m pip install pyyaml
python scripts/validate_config.py
```
