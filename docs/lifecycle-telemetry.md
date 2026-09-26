# Lifecycle telemetry

Issue #46 projects operational telemetry from canonical GitHub Issue/PR history.

This task keeps telemetry strictly derived and advisory:

- canonical task/review state remains the GitHub protocol history;
- queue/review/cycle latency, retries, collisions, lease expiry, and runtime/dispatcher activity are reconstructed from durable events;
- correlation/trace identifiers may aid export but never replace stable task identity;
- external webhook/OpenTelemetry export remains optional and must not be required for correctness;
- export guidance must not expose credentials.

This file intentionally establishes the bounded task branch so the scheduled worker can continue on a pre-authorized target without deriving a write destination from external content.
