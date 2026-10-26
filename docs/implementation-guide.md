# Implementation guide (adopters)

1. **Pick the gateway runtime.** Azure-first: API Management AI gateway (`deploy/apim/policy.xml`). Multi-cloud / on-prem: LiteLLM proxy or Kong AI Gateway. Keep this repo's Python pipeline as the *spec and test oracle* for whichever you choose.
2. **Model the teams.** One `TeamPolicy` per cost centre: allowed models, denied models, allowed MCP tools, monthly tokens, soft-limit %, downgrade model. Store in Git; review via PR.
3. **Build the routing eval set.** 100-300 real (redacted) prompts per task type with reference answers. Run `run_evals` against candidate models monthly; route only on measured results. Re-check when a provider updates a model.
4. **Wire identity.** Validate the caller's OIDC token at the gateway; derive team from a group claim, never from a client header alone.
5. **Safety and PII.** Replace `safety.classify` with a managed classifier; keep regex + checksum PII redaction as a deterministic first pass.
6. **Budgets.** Move the ledger to Redis with atomic INCRBY; alert at soft limit; chargeback monthly.
7. **Cache.** Use real embeddings, team scope, TTL, and exclude prompts containing tool results or user-specific data.
8. **Telemetry.** Export `gen_ai.*` spans with the OTel SDK to your collector; build dashboards for tokens, cost, latency, denials by team.
9. **Audit.** Ship JSONL to the SIEM; keep the HMAC key in a key vault; rotate yearly and record the key id per record.
10. **Rollout.** Shadow mode (log decisions, enforce nothing) for 2 weeks, then enforce deny rules, then budgets.
