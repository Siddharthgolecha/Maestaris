# Scaling

## Scale worker identities, not schedulers

Prefer a small number of generic ChatGPT worker-pool schedules over one scheduled task per specialist.

Static agent config maps specialist identities to pools.

## Discover work with GitHub

Pools search open `maestaris:task` Issues, filter by structured project/worker fields, then inspect comments for authoritative status.

Derived status and priority labels make discovery cheaper but do not replace comment inspection.

## Parallelism

Parallelize independent task Issues.

Do not run multiple workers on the same task unless the protocol explicitly defines collaboration.

## Projects

Use GitHub Projects for human overview and filtering. Auto-add task Issues by label and let closed Issues become Done.

## Large repositories

Use multiple projects, explicit dependencies, priority fields, and bounded `max_tasks_per_run`.

The goal is critical-path progress, not maximum concurrent activity.
