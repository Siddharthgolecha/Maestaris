# GitHub-native integration

Zerion uses GitHub as the live coordination substrate.

## Issues

Each bounded task is an Issue.

The body is the assignment. Comments form the event log.

## Pull requests

Repository-changing work belongs in a linked task PR. Opening it as a draft early exposes work in progress.

A PR is work-plane evidence, not a mailbox and not a mechanism for waking ChatGPT.

## Actions

GitHub Actions react immediately to repository events and are ideal for mechanical work:

- protocol validation;
- label synchronization;
- tests/checks;
- artifact generation.

Actions do not directly invoke an ordinary ChatGPT sidebar conversation.

## Labels

Zerion derives managed labels from the Issue history. By default:

- `zerion:task`
- `zerion:assigned`
- `zerion:claimed`
- `zerion:blocked`
- `zerion:needs-review`
- `zerion:accepted`
- `zerion:revise`
- `zerion:rejected`
- `priority:<value>`

Unmanaged user labels are preserved.

## Native PR reviews

APPROVE may mirror ACCEPTED and REQUEST_CHANGES may mirror REVISE.

GitHub prevents a PR author from approving their own PR. Same-identity setups should use COMMENT or skip native review; the Issue-side Zerion review remains canonical.

## Projects

Projects is an optional derived dashboard. See `docs/github-projects.md`.

## Connected AI runtimes

An AI runtime may have GitHub connector/API access while its shell cannot reach github.com. Zerion therefore makes shell `git`/`gh` optional for agent operation.
