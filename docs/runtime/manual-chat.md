# Manual chat runtime

Maestaris also works without scheduling.

Keep one orchestrator conversation and any number of specialist conversations.

At the start of a turn, tell the chat to use Maestaris on the repository and read `AGENTS.md`.

The chat reconstructs current state from GitHub task Issues/comments and linked evidence rather than relying on prior conversation context.

Typical manual flow:

1. orchestrator creates/updates a task Issue;
2. user opens or returns to the specialist chat;
3. specialist polls GitHub, ACKs, works, and reports;
4. user invokes orchestrator;
5. orchestrator reviews evidence and continues the project.

A fresh specialist conversation can replace an old one as long as GitHub contains the durable state.
