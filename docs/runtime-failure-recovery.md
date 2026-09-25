# Runtime refusal and failover

A provider refusal or tool/runtime denial is evidence about one invocation, not a substantive conclusion about the Maestaris task. Classify it as `provider-policy-refusal`, `tool-auth-denied`, `capability-unavailable`, `provider-outage`, or `malformed-or-irrelevant-refusal`.

If refusal occurs before ACK, leave the task unclaimed. If it occurs after ACK and GitHub is still writable, record a bounded runtime-scoped BLOCKED/release event containing the machine-readable reason and no fabricated task conclusion. If GitHub cannot be written, do nothing destructive: normal ACK lease expiry/recovery returns the task to the shared queue. The same rule applies when refusal happens during review.

A later ChatGPT-, Gemini-style, or other UI-scheduled dispatcher may claim the recovered task only when its own observed capabilities, dependencies, admission policy, and provider controls permit it. It must preserve the original objective rather than substituting unrelated security frameworks or other work. Never reinterpret a benign orchestration request into an unrelated restricted category, and never attempt to bypass, weaken, prompt around, or otherwise circumvent a provider's safety controls.

Preserve exact refusal text only when it is safe and useful; machine-readable classification is normally sufficient and must never copy credentials, secrets, or private data into Issue history.
