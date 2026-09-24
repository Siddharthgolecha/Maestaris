---
name: Maestaris task
about: Create a bounded task in the Maestaris work queue
title: "[Maestaris task] "
assignees: ""
---

[ORCHESTRATOR:v1]
task_id: project-task-0001
project: my-project
priority: P1
depends_on: []

# Optional specialist pin. Omit by default.
# worker: my-project-security

objective: |
  State one bounded outcome.

constraints:
  - Preserve existing canonical results.

completion:
  - Produce durable evidence.
  - Link any task PR to this Issue.
  - Report exact verification performed.

## Queue semantics

An open task Issue is READY by default.

Do not assign a worker merely to put work in the queue. Worker ownership is
established by the first valid unexpired ACK comment.

Use `worker:` only when this task genuinely requires a specific specialist.

## Notes

Optional context. The structured block above is the authoritative task definition.
