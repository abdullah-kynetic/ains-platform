# Model policy

- **No vendor lock-in.** All model calls go through a small provider switch layer; swapping models is a config change.
- **Cheapest model that benchmarks well** for the task, re-checked against current benchmarks before each AI build (don't rely on remembered rankings).
- **Approved providers:** Anthropic and OpenAI (attorney approved verbally — get it in writing before client data is involved). Prefer zero/limited data-retention settings.
- **Never** send SAR material to any model. Never send real client documents to a model without an approved data contract (intake sorting only, never SAR).
- Not approved for client data: model routers/aggregators (e.g. OpenRouter), free-tier proxies such as freellmapi (data retention, unapproved providers, unreliable free tiers).
- Coding agents: Codex CLI (`gpt-6.1-sol`, high effort) for code; Claude Code as orchestrator with parallel threads. These see code and synthetic data only.
- Log model, version, tokens and cost for every production AI call.
