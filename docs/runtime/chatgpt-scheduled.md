# ChatGPT scheduled runtime

Maestaris's primary automation model for ordinary ChatGPT is **scheduled polling**.

A scheduled chat cannot be assumed to receive GitHub webhooks directly.

## Orchestrator schedule

On each run:

1. read Maestaris static config;
2. search relevant task Issues;
3. inspect new terminal worker events and evidence;
4. review/merge/finalize when warranted;
5. create the next bounded Issues.

## Worker-pool schedule

On each run:

1. read pool membership;
2. search open Maestaris task Issues;
3. filter by project/worker/pool;
4. inspect comments for ACK ownership and terminal state;
5. claim at most the configured number of eligible tasks;
6. execute bounded work;
7. report durable results.

## Why polling is safe

Schedules may overlap, retry, or run when nothing is available.

Stable task IDs and ACK leases make repeated polling idempotent.

## What GitHub events do

GitHub events can trigger Actions that validate protocol records, sync labels, run CI, and update dashboard inputs.

They do not directly wake the scheduled/ordinary ChatGPT conversation.

When the user is present, the same worker chat can be invoked immediately instead of waiting for its next scheduled poll.

## Draft-PR fallback for scheduled runtimes

A scheduled runtime may occasionally retain repository-content writes while its direct
pull-request mutation is refused. Once the worker has a canonical ACK, it may continue
bounded durable work on its canonical `maestaris/task/<issue>-<slug>` branch.

Maestaris also ships a GitHub-native fallback on pushes to canonical task branches.
When the branch maps to an open Maestaris task Issue, has commits beyond `main`, and
does not already have an open PR, GitHub Actions opens a **draft** PR to `main` with
`Resolves #<issue>`. This fallback changes no ownership or review state and never
merges automatically. Workers must still satisfy the normal terminal-review gate before
posting `NEEDS_REVIEW`.

