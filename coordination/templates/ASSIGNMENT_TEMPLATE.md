# Suggested Issue title

`[Zerion task] <short bounded objective>`

# Issue body

[ORCHESTRATOR:v1]
task_id: project-task-0001
project: my-project
base: main
priority: P1
depends_on: []

# Optional specialist pin. Omit for ordinary queue work.
# worker: my-project-security

objective: |
  State one bounded objective.

constraints:
  - Preserve existing canonical results.

completion:
  - Produce durable evidence.
  - Link any task PR to this Issue.
  - Report exact verification performed.

## Semantics

Opening the task publishes it to the READY queue.

No worker owns it until a valid ACK is posted.

Use `worker:` only when the orchestrator intentionally restricts eligibility to a
specific specialist.
