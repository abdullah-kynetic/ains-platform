# Model policy

Updated 7 Nov 2026 after the attorney's written sign-off. Abdullah confirmed that the sign-off covers cloud models, including through OpenRouter, and covers real client data. The signed document is kept in the project files, not in this repo, and is not quoted here. If its scope is ever in doubt, read the document, not this summary.

## What is approved
- **Providers:** Anthropic and OpenAI, directly or through OpenRouter. Prefer zero or limited data-retention settings where a provider offers them.
- **No vendor lock-in.** All model calls go through one small provider switch layer; swapping models is a config change.
- **Cheapest model that benchmarks well** for the task, re-checked against current benchmarks before each AI build (don't rely on remembered rankings).
- Free-tier proxies such as freellmapi are still not approved (data retention, unapproved providers, unreliable free tiers).

## Hard limits (unchanged)
- **SAR material never goes to any model, by any route.** This is blocked by item and tag, not just by policy.
- Real client data is covered by the sign-off but **not yet used**: it waits until the build and the security and compliance work are complete and Abdullah says to start. Until then, synthetic data only.
- Intake sorting and the FINRA chatbot are the only planned uses. No model makes or approves a finding or signs a report; only a human does.

## Free-model trial (first two weeks of AI testing)
- Free hosted models only (OpenRouter free models are fine).
- **No paid fallback.** If a free model fails, the call fails.
- The roughly $18 OpenRouter balance stays untouched. Any paid use needs Abdullah's explicit approval first.
- The two weeks start when the test workflow is operational.

## Other
- Coding agents: Codex CLI for code and Claude Code as orchestrator with parallel threads. They see code and synthetic data only.
- Log model, version, tokens and cost for every production AI call, without logging document content.
