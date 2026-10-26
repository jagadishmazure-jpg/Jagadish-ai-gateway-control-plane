# Training module: building a governed AI gateway

**Audience:** AI / platform engineers, 1-2 days.

## Learning objectives
By the end, a trainee can:
1. Explain why model calls and tool calls should share one control plane.
2. Implement deny-by-default, runtime-editable model access per team.
3. Build eval-informed routing and explain why routing must be proven per workload.
4. Implement soft-limit downgrade and hard-limit block budgets.
5. Add PII redaction and content safety *before* the provider and cache.
6. Produce tamper-evident audit logs and OTel GenAI spans.

## Labs
| # | Lab | What to change | Done when |
|---|---|---|---|
| 1 | Run the pipeline | `python scripts/run_eval.py` | You can explain every metric in the README |
| 2 | Runtime deny | Deny `mock-large` for `finance` mid-run | Denials appear in audit with reason |
| 3 | Routing tolerance | Set tolerance 0.0 and 0.10 | You can describe the cost/accuracy trade-off with numbers |
| 4 | Budget tuning | Change `soft_limit_pct` to 0.5 | Downgrade count rises; tests still pass |
| 5 | New PII type | Add IBAN detection with a checksum | New parametrized test passes |
| 6 | Cache safety | Write a test that proves a low threshold returns a wrong answer | Known-failure test added and documented |
| 7 | Tool approvals | Add a `max_rows` argument check for `erp.read` | Test for over-limit read |

## Capstone
Add a **per-user** budget (in addition to per-team), a circuit breaker that stops calling a provider after 3 consecutive failures for 30 seconds, and a `results.json` metric for both. Update the README via `render_readme.py`; CI must stay green.

## Assessment rubric
Correctness (tests), safety (no PII reaches provider in any new path), honesty (numbers labelled simulated), and docs (README regenerated).
