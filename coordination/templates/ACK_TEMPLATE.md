# Post as a comment on the task Issue

[WORKER:worker-name:v1]
task_id: project-worker-0001
status: ACK
dispatcher: chatgpt-pool-A
runtime: chatgpt
instance: optional-stable-scheduler-name
claimed_at: 2026-01-01T00:00:00Z
lease_hours: 3

`dispatcher` identifies the scheduler/dispatcher instance for lease ownership.
`runtime` and `instance` are optional metadata that help multi-AI deployments
debug capacity and populate dashboards; older ACKs without them remain valid.
