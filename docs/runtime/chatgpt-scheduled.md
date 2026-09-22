# ChatGPT scheduled runtime

A ChatGPT scheduled task can act as a Zerion orchestrator or generic worker pool.

Keep runtime-specific timing constraints here rather than in the core protocol. Product limits can change; task IDs, ACK claims, terminal reports, reviews, and repository-first state should remain stable.

Recommended structure:

- one orchestrator schedule;
- a small number of generic worker-pool schedules;
- specialist worker identities stored in GitHub configuration;
- staggered runs when useful;
- immediate manual execution when the user is present.

Do not create one scheduled task per specialist unless there is a clear operational reason.
