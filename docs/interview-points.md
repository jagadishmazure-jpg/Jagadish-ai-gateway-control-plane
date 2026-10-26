# Interview points
- Why a gateway: one place for identity, policy, cost, safety and audit across every model and tool.
- Routing is a hypothesis: route only on measured evals per task; in a prior lab a router lost to the large model (0.58 vs 0.72), so I always prove it.
- Budget downgrade beats hard failure for user experience; hard stop still needed.
- PII redaction runs before both the provider and the cache, otherwise the cache becomes a PII store.
- Cache must be scoped per team/tenant to avoid cross-tenant leakage.
- Audit uses HMAC chaining + pseudonyms: tamper-evident without storing raw identity.
- Same controls map to APIM policies, LiteLLM virtual keys and Kong plugins.
