# Failure recovery

## State points to a stale task Issue

Inspect the Issue and linked PR evidence. Repair the state index to the newest durable GitHub state.

## Two dispatchers race

Both must inspect comments before ACK. The first valid unexpired ACK lease owns the task.

## Worker ACKs and disappears

After lease expiry, record the stale claim on the Issue and reassign or release the task.

## Draft PR exists but no terminal report

Treat the task as still active unless evidence proves otherwise. Inspect checks and recent commits before reassigning.

## Task Issue exists but state index is empty

The Issue is durable evidence. Reconstruct state from its body/comments and linked PR.

## PR exists but is not linked to an Issue

Treat it as an audit problem. Link it to the correct task before relying on it as Zerion work.

## Issue auto-closed too early

Reopen it when the protocol still requires review or revision. Closing keywords are conveniences, not permission to skip evidence review.

## Chat memory disagrees with GitHub

GitHub wins.

## Worker invents a new objective

Reject the scope expansion. Orchestrators create bounded task Issues.

## Negative result disappears

Recover it from Issue comments, commits, or artifacts and restore the state/canonical record without upgrading its classification.

## Legacy mailbox branch contains substantive work

Move substantive changes to a normal task branch/PR. Legacy mailbox PRs remain control-plane-only.
