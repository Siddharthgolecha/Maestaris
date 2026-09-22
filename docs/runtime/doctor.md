# Runtime doctor

`zerion doctor` is an optional capability probe for reproducible handoffs. It reports what the current local execution environment can observe without turning the Zerion CLI into a requirement for AI workers.

```bash
zerion doctor
zerion doctor --json > zerion-runtime.json
```

The JSON form is intended to be attached to an Issue, PR, Actions artifact, or other durable handoff when environment differences matter.

## Output schema

The report has `schema: 1` and `kind: zerion-runtime-capability-report`. It records:

- Python, operating system, architecture, and executable;
- installed Zerion/PyYAML package versions when discoverable;
- presence/version of optional local `git`, `gh`, and `lake` commands;
- whether a local `.git` directory and Zerion registry are present;
- non-secret CI/runtime signals;
- an explicit `connected_services.github: unknown` boundary;
- hosted-CI fallback and claim-semantics notes.

The doctor never reads or prints credential values. In particular, token/API-key presence is not required for the report and token names/values are deliberately excluded.

## Shell access is not connected-service access

A worker may have a connected GitHub tool while lacking `git` or `gh` in its shell. Conversely, a local shell may contain `git` without the AI runtime having permission to invoke a connected GitHub API.

For that reason the doctor reports shell capabilities separately and leaves connected-service access as `unknown`. The invoking runtime should state its connected tools in the task handoff when relevant.

## Missing tools are not automatically blockers

A missing local tool is an observation, not a failed task. If a required verifier is available in GitHub Actions, use hosted CI and cite the check/run as durable evidence. This is especially useful for toolchains such as Lean or provider CLIs that may not be installed in a chat execution environment.

Example handoff:

```text
Local doctor: lake unavailable; git available.
Connected runtime: GitHub repository read/write available through provider connector.
Verification: Lean build delegated to GitHub Actions run <id>; check passed on commit <sha>.
```

Do not promote a capability report into evidence for a scientific or engineering claim. It only says what the environment appears able to run.
