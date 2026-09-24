# Releases and versioning

Maestaris uses semantic versions for published protocol/tooling boundaries.

The package version in `pyproject.toml` is the source of the release tag:

```text
0.6.0 -> v0.6.0
```

## Release policy

A release is created only after the `Validate Maestaris` workflow succeeds on `main`.

The release workflow then:

1. reads the version from `pyproject.toml`;
2. verifies that `CHANGELOG.md` has a matching heading;
3. checks whether `v<version>` already exists;
4. if not, creates a GitHub Release and tag at the validated main commit;
5. if the release already exists, exits without moving the tag.

This makes a version bump an explicit publication decision.

## Semantic version guidance

- patch: fixes/documentation/compatible automation changes;
- minor: backwards-compatible protocol/features;
- major: intentionally incompatible protocol contract.

During early development Maestaris may make larger changes under 0.x, but the release
still marks a durable recovery point.

## Immutable releases and attestations

GitHub supports immutable releases and release attestations. Repository/organization
administrators may enable immutable releases when they want tags and release assets
locked after publication.

For produced binaries/packages/artifacts, add GitHub artifact attestations so users
can verify build provenance.

Release immutability and attestations are a stronger provenance layer than hand-written
hashes alone, but domain-specific manifests may still document assumptions that GitHub
cannot represent.

Official GitHub documentation:

- https://docs.github.com/en/code-security/concepts/supply-chain-security/immutable-releases
- https://docs.github.com/en/actions/concepts/security/artifact-attestations
