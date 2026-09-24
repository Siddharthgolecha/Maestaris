# Failure recovery

## Chat loses context

Read `AGENTS.md`, static project/agent config, then search open Maestaris task Issues and reconstruct state from comments.

## Labels disagree with comments

Comments win. The label workflow should repair derived labels on the next relevant Issue/comment event.

## Project board disagrees with Issues

Issues win. Projects is a view.

## Two workers race

The first valid unexpired ACK owns the task. Later dispatchers must stop after reading the Issue comments.

## Worker ACKs and disappears

After the lease expires, the orchestrator may record the stale claim and allow reassignment.

## Draft PR exists with no terminal report

Inspect commits/checks and the ACK lease before reassigning. A draft PR alone does not prove completion.

## Issue has terminal result but no review

The orchestrator reviews the durable evidence and records ACCEPTED, REVISE, or REJECTED.

## PR exists but is not linked to a task

Treat it as an audit problem. Link it to the correct Issue before relying on it as Maestaris work.

## GitHub event fired but ChatGPT did nothing

Expected. GitHub events trigger Actions, not ordinary ChatGPT conversations. The worker will act when manually invoked or when its ChatGPT schedule polls GitHub.

## Negative result disappears from a summary

Recover from Issue comments, PRs, commits, checks, or artifacts. Durable evidence wins over prose summaries.
