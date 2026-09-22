[ORCHESTRATOR:v1]
task_id: project-worker-0001
project: my-project
worker: worker-name
status: ASSIGNED
base: main
priority: P1
depends_on: []
objective: |
  State one bounded objective.
constraints:
  - Preserve existing canonical results.
completion:
  - Produce durable evidence in a task PR.
  - Report exact verification performed.
