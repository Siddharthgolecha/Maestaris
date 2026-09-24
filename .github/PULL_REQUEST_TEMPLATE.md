## Maestaris task

Maestaris-Task: #<issue-number>

Use a GitHub closing keyword when this PR should complete the task on merge, for example:

`Resolves #<issue-number>`

For long-running work, open the PR as a **draft** soon after ACK so the work plane is visible without pretending it is complete.

## Summary

## Durable evidence

## Verification

## Claim / classification changes

## Idempotency / recovery impact

- [ ] Linked to the correct Maestaris task Issue
- [ ] `maestaris validate`
- [ ] Relevant tests / CI / proof / experiment passed
- [ ] Fresh worker can reconstruct required state from repository + GitHub Issue/PR evidence
- [ ] No secrets or project-specific private data added
