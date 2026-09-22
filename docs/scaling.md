# Scaling

Zerion scales by keeping task identity native to GitHub.

## Worker pools

Use a small number of generic dispatcher pools. Pools inspect state indexes and open task Issues for eligible workers.

Respect `max_tasks_per_run` and ACK leases.

## Issue discovery

At larger scale, use GitHub search, optional labels, milestones, or Projects views to narrow open Zerion tasks.

Suggested optional labels:

```text
zerion
zerion:task
zerion:blocked
priority:P0
priority:P1
```

Labels are discoverability aids, not protocol state.

## Dependencies

Keep explicit `depends_on` task IDs in assignments. GitHub Projects or issue relationships may visualize dependencies when available, but durable protocol fields remain portable across runtimes.

## Milestones and Projects

Milestones are useful for releases or research phases. GitHub Projects can provide a board/dashboard. Neither is required because connected AI runtimes may not expose every native surface.

## Parallelism

Parallelize independent Issues, not duplicate workers on the same task. The objective is critical-path progress, not maximum agent activity.
