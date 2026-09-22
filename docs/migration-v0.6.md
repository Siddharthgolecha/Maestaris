# Migrating to Zerion v0.6 / protocol v4

Protocol v4 separates **available work** from **worker ownership**.

## Old model

A task body often contained:

```text
worker: unassigned
status: ASSIGNED
```

This made backlog work look owned even when no worker had claimed it.

## New model

New task bodies should normally contain only the bounded work definition:

```text
[ORCHESTRATOR:v1]
task_id: example-task-0001
project: example-project
priority: P1
depends_on: []

objective: |
  ...
```

An open task is READY by default.

The first valid unexpired ACK establishes the worker identity and lease.

## Optional worker pin

If a task genuinely requires one specialist, keep:

```text
worker: example-security-auditor
```

This restricts eligibility; it does not itself establish ownership.

## Existing tasks

For unclaimed backlog tasks:

1. remove `worker: unassigned`;
2. remove `status: ASSIGNED`;
3. trigger the Zerion Issue workflow;
4. confirm the derived label becomes `zerion:ready`.

For already-claimed tasks, it is safe to remove the initial status field because the
ACK comment preserves ownership. A real worker pin may remain.

Legacy `status: ASSIGNED` remains parseable during migration, but new task templates
do not emit it.

## Labels

`zerion:assigned` is replaced by `zerion:ready`.

Other derived labels are unchanged.

## Worker pools

Pools should select the highest-priority eligible READY (or revision) task, inspect
dependencies and ACK history, choose a suitable worker if the task is not pinned, and
then post ACK as that worker.

## Validation

Run:

```bash
zerion validate
python -m unittest discover -s tests -v
```
