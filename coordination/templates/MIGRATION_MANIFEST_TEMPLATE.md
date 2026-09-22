# Migration Manifest

Last updated: <YYYY-MM-DD>

This manifest records historically important artifacts and whether they have been
imported and independently reverified in the canonical repository.

| Source artifact | Canonical path | Original claim / role | Reproduction command | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| <artifact> | `path` | <claim/role> | `command` | migration-pending | <notes> |

## Status vocabulary

- `reproduced`
- `reproduced-with-correction`
- `superseded`
- `failed-reproduction`
- `provenance-only`
- `migration-pending`

## Migration rules

1. Prefer historically important source plus negative/falsifying results, not only the
   newest successful output.
2. Preserve raw historical data unchanged when possible.
3. Put newly reproduced outputs beside historical outputs rather than overwriting them.
4. Record environment/toolchain/backend details needed to reproduce the comparison.
5. Do not promote a claim merely because it was described as proved in a prior chat or
   file.
6. Update the evidence ledger only after the migrated result has been independently
   checked to the project's required standard.
