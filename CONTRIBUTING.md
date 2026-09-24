# Contributing

Contributions are welcome. Keep changes small, reviewable, and aligned with Maestaris's repository-first invariant.

For protocol changes, explain:

1. the failure mode being addressed;
2. whether the change is runtime-independent or adapter-specific;
3. how repeated execution remains idempotent;
4. how a new worker reconstructs state from GitHub alone;
5. migration impact for existing projects.

Please include tests or validation updates when modifying schemas or scripts.
