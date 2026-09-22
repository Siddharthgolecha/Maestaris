# Scaling

Prefer a small number of generic worker pools over one scheduler per specialist.

Workers are registered in GitHub and mapped to pools. Pools discover eligible workers, claim tasks, and execute under specialist identities.

Useful scheduling fields include:

```yaml
priority: P0
depends_on:
  - earlier-task
blocked_by: null
```

Larger installations may set a safe per-run cap such as `max_tasks_per_run: 2`, executing only independent tasks.

The objective is not maximum activity. It is maximum useful critical-path progress.
