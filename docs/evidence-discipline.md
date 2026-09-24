# Evidence discipline

Maestaris coordinates work. Coordination is not evidence.

This optional layer is adapted from practices that proved useful in the
`Siddharthgolecha/research-workbench` repository:

- a high-level work index is separate from a detailed claim ledger;
- claim status changes require durable supporting evidence;
- coordination comments cannot silently promote a claim;
- negative/falsifying results remain part of the record;
- migrated historical work is classified by reproduction status;
- a handoff is complete only when a fresh worker can reproduce or inspect the result
  from committed artifacts.

This layer is especially useful for research, experiments, benchmarks, formal
verification, model evaluation, and other work where "what is currently believed"
must be distinguished from "what was actually demonstrated."

## 1. Separate work status from claim status

A **work index** answers:

- What programs/workstreams exist?
- What is active, dormant, blocked, frozen, or complete?
- Where is their canonical material?
- What is the current next objective?

An **evidence ledger** answers:

- What exact claim is being made?
- What evidence class supports it?
- Where is the evidence?
- What limitations or assumptions remain?

Do not collapse these into one document.

A branch can be complete while its scientific claim remains conditional or falsified.
A project can be active while a particular claim is frozen.

## 2. Coordination metadata cannot promote evidence

These are coordination events:

- task assignment;
- ACK;
- DONE / BLOCKED / NEEDS_REVIEW;
- ACCEPTED / REVISE / REJECTED;
- GitHub labels;
- GitHub Project fields.

They describe workflow state.

They do **not** by themselves establish that a theorem is proved, an experiment
succeeded, a benchmark generalized, or a claim is true.

An evidence-status change should point to the durable proof, test, dataset, run,
artifact, or external source that warrants it.

## 3. Suggested evidence classes

Projects may define their own taxonomy. For research-heavy work, the following
classes are useful defaults:

- `kernel-proved`: checked by the relevant proof kernel in a clean committed build;
- `computationally-verified`: deterministic/exhaustive computation establishes the
  claim within an explicitly stated finite domain;
- `empirically-supported`: experiment/simulation supports the claim but does not
  establish an exhaustive theorem;
- `conditional`: the conclusion follows only given explicit assumptions;
- `conjecture`: plausible but not yet proved/tested;
- `falsified`: the tested formulation failed; preserve the counterevidence;
- `migration-pending`: historical work exists but has not yet been imported and
  independently reverified in the canonical repository.

These names originate in the research-workbench discipline. They are examples, not
a universal ontology for every Maestaris project.

## 4. Preserve negative results

Never overwrite or delete a falsifying result merely because a newer model performs
better.

A later result may supersede an implementation or invalidate an old assumption, but
the older negative evidence should remain locatable with its original scope.

Useful distinctions include:

- superseded implementation;
- falsified claim;
- failed reproduction;
- negative control;
- out-of-domain result;
- inconclusive result.

## 5. Migration and reproduction statuses

When importing historical work, classify the artifact rather than silently treating it
as current evidence.

Recommended statuses:

- `reproduced`
- `reproduced-with-correction`
- `superseded`
- `failed-reproduction`
- `provenance-only`
- `migration-pending`

The historical bytes and newly reproduced outputs should normally be preserved
separately.

## 6. Durable handoff contract

A substantive branch is handoff-ready when another fresh conversation can recover
its result from durable artifacts alone.

For computational or research work, a strong handoff contains:

1. source / implementation;
2. raw inputs or an explicit input schema/source;
3. exact reproduction command or workflow;
4. environment/toolchain/backend details when material;
5. assumptions and scope;
6. raw output or preserved artifact;
7. derived analysis kept separate from raw evidence;
8. evidence/claim classification;
9. limitations, blockers, and negative evidence;
10. commit / PR / CI / proof / artifact references.

Avoid handoffs that rely on phrases such as "as proved earlier" without a durable
path or reference.

## 7. Suggested project layout

Projects that need evidence discipline can add:

```text
project/
  WORK_INDEX.md
  EVIDENCE_LEDGER.md
  provenance/
  migration/
  results/
```

Maestaris provides templates under `coordination/templates/`.

These files are project-domain state, not Maestaris's live orchestration state.

## 8. Blind or preregistered work

For blind/preregistered workflows:

- freeze the analyzer/protocol before opening protected results;
- record immutable source/protocol hashes when appropriate;
- separate raw handoff data from target-informed analysis;
- do not tune assumptions or thresholds after observing the protected outcome unless
  the analysis is clearly labeled post hoc;
- preserve failed/falsifying prospective results.

## 9. Auditing

A Maestaris auditor should distinguish:

- **workflow consistency** — Issue/ACK/PR/review state;
- **evidence consistency** — whether the claimed status is actually supported by the
  referenced durable evidence.

An ACCEPTED Maestaris task can legitimately conclude:

> The experiment ran correctly and falsified the tested claim.

That is successful work with a negative scientific result.

## 10. Optionality

This layer is optional.

A simple software project may need only Issues, PRs, tests, and release notes.

A research program may need the full work-index/evidence-ledger/provenance structure.

Maestaris should coordinate both without confusing workflow completion with truth.
