# API-agent runtime

API agents are an optional Zerion runtime.

They use the same GitHub-native protocol as ordinary ChatGPT workers:

- search task Issues;
- inspect event history;
- ACK with leases;
- create linked work PRs;
- report terminal state;
- inspect durable evidence.

API implementations may receive webhooks or dispatch immediately, unlike ordinary ChatGPT sidebar conversations.

That runtime difference must not change the repository protocol. A task created by an API agent should remain understandable to an ordinary ChatGPT worker and vice versa.
