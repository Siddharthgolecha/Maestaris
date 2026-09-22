# API-agent runtime

API agents can implement Zerion's worker or orchestrator roles by reading the same repository configuration and mailbox protocol.

An API integration should:

1. read canonical state before work;
2. enforce task claims and lease semantics;
3. isolate substantive work onto task branches;
4. record durable evidence;
5. preserve idempotency under retries;
6. avoid treating generated summaries as authoritative when repository evidence differs.

API agents are an optional runtime, not a requirement of the Zerion protocol.
