# Failure recovery

## Worker repeats completed work

Use stable task IDs and check for terminal results before execution.

## Two dispatchers race

Give each worker a configured pool and require ACK before substantive work.

## Worker ACKs and disappears

Use an ACK lease. After expiry, the orchestrator may mark the claim stale and reassign the task.

## Chat memory disagrees with repository state

Repository state wins.

## Worker invents a new objective

Reject the scope expansion. Workers execute bounded assignments; orchestrators select the next major objective.

## Negative result disappears

Preserve failed or falsifying results as durable evidence. A later interpretation may contextualize them but should not silently rewrite them as success.

## Mailbox branch contains substantive work

Move the substantive change to a task branch/PR. Mailboxes are control-plane channels only.

## Worker is genuinely blocked

A precise blocker is a valid result. Report the first exact missing dependency, failed assumption, permission issue, unavailable artifact, or verification failure.
