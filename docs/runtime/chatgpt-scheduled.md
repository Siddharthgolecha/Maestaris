# ChatGPT scheduled runtime

Zerion's primary automation model for ordinary ChatGPT is **scheduled polling**.

A scheduled chat cannot be assumed to receive GitHub webhooks directly.

## Orchestrator schedule

On each run:

1. read Zerion static config;
2. search relevant task Issues;
3. inspect new terminal worker events and evidence;
4. review/merge/finalize when warranted;
5. create the next bounded Issues.

## Worker-pool schedule

On each run:

1. read pool membership;
2. search open Zerion task Issues;
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
