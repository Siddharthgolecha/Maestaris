# Multi-orchestrator review leases

When more than one orchestrator runtime polls the same Zerion repository, review ownership is coordinated through the task Issue history.

Before substantive review of an unreviewed terminal worker result, an orchestrator posts:

```text
[ORCHESTRATOR-CLAIM:v1]
task_id: <task-id>
orchestrator: <stable-orchestrator-id>
runtime: <optional-runtime>
instance: <optional-instance>
claimed_at: <UTC timestamp>
lease_hours: <positive duration>
```

The first valid unexpired claim owns that review. Another orchestrator must skip it. The same orchestrator may renew its lease. Once a claim expires, another orchestrator may recover the review. A terminal `[ORCHESTRATOR-REVIEW:v1]` consumes the active claim.

Review claims are arbitration metadata only: they do not change the task's derived READY/claimed/needs-review/reviewed status, and they do not replace evidence inspection. GitHub Issue history remains canonical.
