## Verified task checkpoints

Checkpoints are optional progress evidence for long-running tasks. They do not claim a task, extend an ACK lease, satisfy terminal evidence, or replace Issue history.

A checkpoint records a stable ID, source commit, deterministic fingerprint of checkpoint-relevant inputs, immutable artifact hashes, and whether outputs were verified. Reuse after lease expiry is allowed only when the source still exists, inputs are unchanged, and every reused artifact is present and hash-valid.

Changed inputs explicitly invalidate the checkpoint. Missing or unverified artifacts are recomputed rather than trusted. Legacy tasks continue normally without checkpoints.

Raw and derived outputs should be distinguished. If raw computation succeeded and is verified, a later presentation or packaging failure reuses that raw artifact and regenerates only the failed derived layer.

CHECKPOINT comments remain durable provenance in canonical Issue history but are non-terminal; normal worker terminal reports and orchestrator review retain their protocol meanings.
