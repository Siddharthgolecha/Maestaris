# Evidence Ledger

This ledger records exact claims separately from project/workflow status.

| ID | Area | Claim | Status | Evidence | Limitations / assumptions |
| --- | --- | --- | --- | --- | --- |
| EXAMPLE-1 | example | State one bounded claim. | conjecture | `path/to/evidence` | Explicitly state scope and what is not established. |

## Suggested status vocabulary

Use a project-specific vocabulary when appropriate. Research-heavy defaults:

- `kernel-proved`
- `computationally-verified`
- `empirically-supported`
- `conditional`
- `conjecture`
- `falsified`
- `migration-pending`

## Promotion rule

Changing a claim status is an evidence action.

Record:

- the supporting commit/data/proof/run/source;
- assumptions that remain;
- scope/domain of the result;
- negative or conflicting evidence.

Never promote a claim solely because a Zerion task was marked DONE or ACCEPTED.
