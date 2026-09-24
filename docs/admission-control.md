# Fair-share and named-resource admission

Admission control is an optional gate applied **after** canonical task state, dependencies, ownership/backpressure, hard capabilities, and explicit priority have been resolved, but before ACK. It never promotes lower-priority work above P0: priority remains the primary scheduler ordering.

Repositories may configure fair-share limits for stable producer/workflow/tenant group names and named resource capacities such as `github-api`, `expensive-model`, `gpu`, or `deployment`. Tasks may request a `fair_share_group` and a `resources` mapping of resource name to slots. These declarations belong in durable task/project configuration or Issue records; GitHub Project fields remain derived views.

`zerion_orchestration.admission.admission_decision` is the provider-neutral reference projection. Its `active` input must contain only currently valid canonical ACK/resource leases reconstructed from Issue history. Consequently an expired owner stops consuming capacity without deleting or rewriting its historical ACK. Unknown requested named resources fail closed when named-resource admission is in use; repositories with no admission configuration retain legacy lightweight behavior.

Fair-share accounting is deliberately same-priority. It prevents one configured group from consuming all same-priority capacity while avoiding any fairness score that could demote P0 below P1/P2. Named-resource accounting is independent of provider identity and prevents the sum of active slots plus a candidate request from exceeding the configured limit.

A dispatcher should record only the normal ACK after admission succeeds. Capacity is reconstructed from those unexpired leases; there is no mutable semaphore file. A failed admission is a scheduling decision, not a task failure, and should not erase blocked/negative evidence or consume a retry attempt.
