# Migrating to Zerion v0.5

v0.5 is intentionally breaking.

It removes the shadow mutable state introduced in earlier releases.

## Removed

Delete:

```text
coordination/state/
coordination/mailboxes/
coordination/schema/state.schema.json
coordination/templates/STATE_TEMPLATE.yaml
```

Remove from project/agent YAML:

- `mailboxes`
- `mailbox`
- `current_task`
- `current_objective`

PR-backed mailbox transport is no longer supported.

## Update global registry

Set:

```yaml
protocol_version: 3

github:
  task_transport: issue
  task_label: "zerion:task"
  ...
```

Use the current `coordination/zerion.yaml` as the reference.

## Preserve history

Do **not** delete old GitHub mailbox PRs or task evidence merely because v0.5 no longer routes through them.

Closed/old PRs remain useful provenance.

## Cut over live work

For each active task:

1. create a structured Zerion task Issue if one does not already exist;
2. copy only the current assignment/blocker/result references needed for continuity;
3. link existing task PRs/commits/evidence;
4. record the current valid ACK if a worker still owns the task;
5. continue future protocol events on the Issue.

Do not migrate every historical comment merely to recreate chat history.

## Projects

After v0.5 Actions are active, configure a GitHub Project auto-add workflow with:

```text
is:issue label:"zerion:task"
```

Projects is optional and derived.

## Validate

Run:

```bash
zerion validate
```

Protocol v3 validation deliberately fails if removed state/mailbox files remain.
