"""SIMULATED run: synthetic prompts + mock providers. Writes results/results.json."""
import json, pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gateway.gateway import Gateway, Request  # noqa: E402
from gateway.policy import PolicyStore, TeamPolicy  # noqa: E402
from gateway.providers import CATALOG, MockProvider, cost  # noqa: E402
from gateway.router import Router, classify_task, run_evals  # noqa: E402
from gateway.workload import make_set, make_workload  # noqa: E402

ALL = set(CATALOG)
def policies():
    return PolicyStore([
        TeamPolicy("support", ALL, allowed_tools={"kb.search", "ticket.write"}, monthly_tokens=40_000),
        TeamPolicy("finance", ALL - {"mock-selfhosted"}, allowed_tools={"erp.read"}, monthly_tokens=40_000),
        TeamPolicy("engineering", ALL, allowed_tools={"repo.read"}, monthly_tokens=5_000),
    ])

def main():
    prov = MockProvider()
    table = run_evals(make_set(200, seed=7), prov)          # routing evals (separate seed from workload)
    work = make_workload(2000, seed=42)
    gw = Gateway(policies(), Router(table), prov)
    res = [gw.chat(Request(**w)) for w in work]
    ok = [r for r in res if r["status"] == "ok"]
    # baseline: the SAME served requests sent to the large model, no cache (like-for-like)
    base_cost = base_correct = 0
    for w, r in zip(work, res):
        if r["status"] == "ok":
            b = prov.complete("mock-large", w["prompt"], classify_task(w["prompt"]))
            base_cost += cost("mock-large", b["tokens_in"], b["tokens_out"]); base_correct += b["correct"]
    n_base = len(ok)
    denied = [r["reason"].split(":")[0] for r in res if r["status"] == "denied"]
    gw_cost = sum(r["usd"] for r in ok)
    metrics = {
        "Requests": len(work),
        "Served": len(ok),
        "Blocked by content safety": denied.count("content_safety"),
        "Blocked by hard budget": denied.count("budget"),
        "Downgraded by soft budget": sum(1 for r in ok if r["note"].startswith("downgraded")),
        "Requests with PII redacted": sum(1 for r in ok if r["pii_redacted"]),
        "Semantic cache hit rate": f"{sum(r['cache'] for r in ok) / len(ok):.1%}",
        "Accuracy, gateway (synthetic)": f"{sum(r['correct'] for r in ok) / len(ok):.1%}",
        "Accuracy, always-large baseline (synthetic)": f"{base_correct / n_base:.1%}",
        "Illustrative cost, gateway (USD)": f"{gw_cost:.4f}",
        "Illustrative cost, always-large baseline (USD)": f"{base_cost:.4f}",
        "Cost reduction vs baseline": f"{1 - gw_cost / base_cost:.1%}",
        "Audit chain verified": gw.audit.verify(),
        "OTel-style spans emitted": len(gw.tracer.spans),
    }
    out = {"label": "SIMULATED: synthetic prompts, mock providers, illustrative prices",
           "sample": "2,000 synthetic requests, 3 teams, seed 42; routing evals on 800 separate prompts",
           "metrics": metrics, "routing_eval_table": table}
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "results.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(metrics, indent=2))

if __name__ == "__main__":
    main()
