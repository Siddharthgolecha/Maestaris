# Independent verification policy

Independent verification is an optional acceptance gate. GitHub Issue history remains canonical; this policy does not create mutable reviewer state or make Project fields authoritative.

A task or project may declare a `review_policy` with these portable keys:

```yaml
review_policy:
  min_reviewers: 1
  different_worker: false
  different_runtime: false
  require_ci: false
  require_evidence: false
```

Omitting `review_policy` preserves legacy single-review behavior. `different_worker` excludes the implementation worker. `different_runtime` requires a verification record whose runtime differs from the implementation runtime; missing runtime metadata cannot prove that constraint. `min_reviewers` counts distinct reviewer identities, not repeated records. `require_ci` and `require_evidence` are explicit gates evaluated from durable linked checks/artifacts.

Verification records are evidence, not ownership. A portable record uses a durable Issue comment such as:

```text
[VERIFICATION:v1]
task_id: <task-id>
status: VERIFIED
reviewer: <stable reviewer identity>
runtime: <runtime when relevant>
evidence: <PR/check/artifact/commit references>
```

The orchestrator reconstructs implementation ownership/runtime and verification records from GitHub, evaluates `zerion_orchestration.verification.verification_decision`, and must not post `ACCEPTED` while a configured policy is unsatisfied. Review-claim arbitration remains separate: holding an orchestrator review lease does not itself satisfy independent verification.

Provider/runtime metadata remains advisory unless a task explicitly requests runtime independence. A provider self-description is not verification evidence; the referenced checks/artifacts must be inspected normally.