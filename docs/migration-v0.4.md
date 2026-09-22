# Migrating from PR mailboxes to GitHub task Issues

Zerion v0.4 keeps legacy PR-backed mailboxes readable but recommends GitHub task Issues for new work.

## Safe migration

1. Finish or explicitly freeze any task currently claimed through a legacy mailbox.
2. Preserve the mailbox PR and its comments as historical provenance; do not delete it.
3. Change the project configuration to:

```yaml
control_plane:
  transport: github_issue
```

4. Change each worker agent configuration to the same transport.
5. Remove the legacy `mailboxes` mapping once it is no longer used for active routing.
6. Remove `mailbox.pr` from new worker state and ensure `task.issue` exists.
7. Create future bounded assignments as `[Zerion task]` Issues.
8. Run `zerion validate`.

## During a mixed migration

Do not split one worker's active task across both transports.

A project/worker should either:

- finish its current legacy mailbox task and then switch; or
- remain on legacy transport until a clean cutover point.

Historical PR mailbox comments remain valid evidence even after the project switches to Issues.

## Why migrate

Issues are a better native coordination primitive:

- no fake branch is needed;
- stable Issue numbers identify tasks;
- comments form a natural event log;
- open/closed state and close reasons map to task lifecycle;
- PRs can link and auto-close Issues;
- milestones, Projects, labels, and assignees can provide optional views.
