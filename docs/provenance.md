# Native-first provenance bundles

Maestaris treats provenance as evidence, not as a second mutable state machine. Prefer GitHub-native immutable or durable objects wherever they already express the required fact.

## Native mapping

| Provenance fact | Preferred GitHub primitive |
| --- | --- |
| exact source | commit SHA and signed/annotated tag where appropriate |
| published bundle | GitHub Release and release assets |
| build/test output | Actions run, check, and retained workflow artifact |
| build provenance | GitHub artifact attestation when supported |
| release integrity | immutable release settings when available, plus asset digests |
| task/review history | Maestaris Issue protocol and linked PR |

A repository manifest is justified only for semantics GitHub does not represent well: raw-vs-derived classification, exact reproduce commands, domain assumptions, blind-analysis constraints, recovery notes, and relationships among externally produced artifacts.

## Optional `PROVENANCE.json`

A release or experiment may include a `PROVENANCE.json` beside its artifacts. It is intentionally small and domain-neutral:

```json
{
  "schema": 1,
  "source": {"commit": "<40-hex-sha>", "version": "<optional-tag>"},
  "artifacts": [
    {"path": "raw/results.csv", "sha256": "<64-hex>", "kind": "raw"},
    {"path": "derived/summary.json", "sha256": "<64-hex>", "kind": "derived"}
  ],
  "environment": {"report": "environment.json"},
  "reproduce": {"command": "python scripts/reproduce.py"},
  "validation": {"report": "validation.json"},
  "recovery": {"recompute_required_if_packaging_fails": false},
  "notes": []
}
```

`kind` is `raw`, `derived`, or `metadata`. Raw bytes should be preserved whenever possible. A failure while packaging Markdown, checksums, or a release must not be interpreted as corruption of raw scientific/data artifacts and must not trigger recomputation unless integrity verification actually fails.

## Bundle procedure

1. Freeze the source commit and, for publication, a release tag.
2. Preserve raw outputs byte-for-byte. Compute SHA-256 for every bundle artifact.
3. Generate environment and validation reports without embedding credentials.
4. Record the exact reproduce command and classify artifacts as raw/derived/metadata.
5. Validate all declared files and hashes before publishing.
6. Upload the validated bundle as release assets or Actions artifacts as appropriate.
7. Generate artifact attestations when the repository/runtime supports them.
8. Link the Release/run/attestation from the relevant Maestaris task Issue so a fresh agent can reconstruct the evidence chain.

## Recovery semantics

Packaging is downstream of computation. If report rendering, checksum formatting, upload, or release creation fails after raw outputs have been verified, retry packaging from the preserved artifacts. Do not rerun expensive experiments merely to repair presentation metadata. Recompute only when the raw artifact is absent, corrupt, or explicitly invalidated by the domain workflow.

## Verification handoff

A durable handoff should name the source commit/tag, Release or Actions run, attestation when present, manifest/hash verification result, exact reproduce command, and any unsupported native feature. Absence of an attestation must be reported honestly rather than replaced by a claim of cryptographic provenance.
