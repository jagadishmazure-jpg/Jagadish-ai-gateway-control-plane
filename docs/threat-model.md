# Threat model (STRIDE + OWASP LLM Top 10)

| Threat | Example | Control in this repo | Gap |
|---|---|---|---|
| Spoofing | Caller claims another team | Team must exist in policy store | Real OIDC validation is in deployment configs only |
| Tampering | Edit audit records | HMAC chain, `verify()` | Key in env var in lab; use a vault |
| Repudiation | "I never called that model" | Pseudonymised audit per request | — |
| Information disclosure (LLM02) | PII sent to a provider / cached | Redaction before provider and cache; team-scoped cache | Regex misses free-text PII like names |
| Denial of service / cost (LLM10 unbounded consumption) | Runaway agent loop | Soft/hard token budgets | Per-process ledger |
| Elevation of privilege (LLM06 excessive agency) | Agent calls a write tool | Tool allow-list + approval id for `.write` | Approval id not cryptographically verified in lab |
| Prompt injection (LLM01) | "Ignore previous instructions" | Not solved here | See Jagadish-prompt-injection-evals |
