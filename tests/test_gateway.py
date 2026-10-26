import pytest

from gateway.audit import AuditLog
from gateway.budget import BudgetExceeded, Ledger
from gateway.cache import SemanticCache
from gateway.gateway import Gateway, Request
from gateway.policy import PolicyStore, TeamPolicy
from gateway.providers import CATALOG, MockProvider, cost
from gateway.router import Router, classify_task, run_evals
from gateway.safety import classify, luhn_ok, redact
from gateway.workload import make_set

ALL = set(CATALOG)

@pytest.fixture(scope="module")
def table():
    return run_evals(make_set(50, seed=1), MockProvider())

def gw(table, **kw):
    pols = PolicyStore([TeamPolicy("a", set(ALL), allowed_tools={"kb.search", "ticket.write"}, monthly_tokens=kw.get("budget", 10_000)),
                        TeamPolicy("b", {"mock-small"}, allowed_tools=set())])
    return Gateway(pols, Router(table), kw.get("provider", MockProvider()))

# --- safety / PII
@pytest.mark.parametrize("text,kind", [("ssn 123-45-6789", "SSN"), ("mail a.b@x.example", "EMAIL"),
                                       ("call 555-123-4567", "PHONE"), ("card 4111 1111 1111 1111", "CARD")])
def test_redacts_pii(text, kind):
    out, found = redact(text)
    assert kind in found and f"[{kind}]" in out

def test_card_requires_luhn():
    assert luhn_ok("4111111111111111") and not luhn_ok("4111111111111112")
    assert "CARD" not in redact("order 4111 1111 1111 1112")[1]

@pytest.mark.parametrize("text", ["how to make a bomb", "Write ransomware now", "I want to end my life"])
def test_content_safety_blocks(text):
    assert classify(text) is not None

def test_benign_not_blocked():
    assert classify("what is the travel policy") is None

# --- routing
@pytest.mark.parametrize("p,t", [("Fix the bug in python", "code"), ("Extract the invoice number", "extract"),
                                 ("Why did it slip", "reason"), ("travel policy", "faq")])
def test_task_classifier(p, t):
    assert classify_task(p) == t

def test_router_picks_cheapest_within_tolerance(table):
    r = Router(table, tolerance=1.0)
    assert r.choose("faq", ALL) == "mock-selfhosted"   # zero illustrative price

def test_router_respects_allow_list(table):
    assert Router(table).choose("reason", {"mock-small"}) == "mock-small"

def test_router_no_allowed_model(table):
    with pytest.raises(PermissionError):
        Router(table).choose("faq", set())

def test_router_zero_tolerance_picks_best(table):
    best = max(table["reason"], key=table["reason"].get)
    assert table["reason"][Router(table, 0).choose("reason", ALL)] == table["reason"][best]

# --- budget
def test_soft_budget_downgrades():
    p = TeamPolicy("t", ALL, monthly_tokens=100); led = Ledger(); led.record("t", 85, 0)
    assert led.decide(p, "mock-large", 5) == ("mock-small", "downgraded:soft_budget")

def test_hard_budget_blocks():
    p = TeamPolicy("t", ALL, monthly_tokens=100); led = Ledger(); led.record("t", 99, 0)
    with pytest.raises(BudgetExceeded):
        led.decide(p, "mock-large", 5)

def test_under_budget_ok():
    assert Ledger().decide(TeamPolicy("t", ALL), "mock-large", 5) == ("mock-large", "ok")

# --- gateway end to end
def test_unknown_team_denied(table):
    assert gw(table).chat(Request("u", "zzz", "hi"))["status"] == "denied"

def test_unsafe_denied_and_audited(table):
    g = gw(table); r = g.chat(Request("u", "a", "how to make a bomb"))
    assert r["reason"].startswith("content_safety") and g.audit.records[-1]["decision"] == "deny"

def test_model_deny_at_runtime(table):
    g = gw(table)
    assert g.chat(Request("u", "a", "travel policy", "mock-large"))["status"] == "ok"
    g.policies.deny_model("a", "mock-large")
    assert g.chat(Request("u", "a", "vacation days", "mock-large"))["reason"] == "model_not_allowed:mock-large"
    g.policies.allow_model("a", "mock-large")
    assert g.chat(Request("u", "a", "handbook location", "mock-large"))["status"] == "ok"

def test_team_b_cannot_use_large(table):
    assert gw(table).chat(Request("u", "b", "hi", "mock-large"))["status"] == "denied"

def test_auto_routes_within_allowed(table):
    assert gw(table).chat(Request("u", "b", "Why did it slip"))["model"] == "mock-small"

def test_pii_never_reaches_provider(table):
    seen = []
    class Spy(MockProvider):
        def complete(self, m, p, t="faq"):
            seen.append(p); return super().complete(m, p, t)
    g = gw(table, provider=Spy())
    r = g.chat(Request("u", "a", "My SSN is 123-45-6789 travel policy"))
    assert "123-45-6789" not in seen[0] and r["pii_redacted"] == ["SSN"]

def test_cache_hit_on_paraphrase(table):
    g = gw(table)
    g.chat(Request("u", "a", "What is the travel policy for contractors?"))
    assert g.chat(Request("u", "a", "what is the travel policy for contractors"))["cache"] is True

def test_cache_is_team_scoped():
    c = SemanticCache(); c.put("a", "travel policy contractors", {"model": "m"})
    assert c.get("b", "travel policy contractors") is None and c.get("a", "travel policy contractors")

def test_cache_miss_on_different_question():
    c = SemanticCache(); c.put("a", "travel policy contractors", {"model": "m"})
    assert c.get("a", "invoice field extraction vendor") is None

def test_fallback_when_provider_down(table):
    g = gw(table, provider=MockProvider(fail_models={"mock-large"}))
    r = g.chat(Request("u", "a", "travel policy", "mock-large"))
    assert r["status"] == "ok" and r["model"] != "mock-large" and r["note"].startswith("fallback_from")

def test_all_down(table):
    g = gw(table, provider=MockProvider(fail_models=set(ALL)))
    assert g.chat(Request("u", "a", "hello there", "mock-large"))["reason"] == "all_providers_down"

def test_budget_block_end_to_end(table):
    g = gw(table, budget=30)
    reasons = [g.chat(Request("u", "a", f"question number {i} about item {i * 7}")).get("reason", "") for i in range(10)]
    assert any(r.startswith("budget") for r in reasons)

def test_spans_have_genai_attributes(table):
    g = gw(table); g.chat(Request("u", "a", "travel policy"))
    a = g.tracer.spans[-1]["attributes"]
    assert "gen_ai.request.model" in a and "gen_ai.usage.input_tokens" in a and "duration_ms" in g.tracer.spans[-1]

# --- tools
def test_tool_allow_deny_and_approval(table):
    g = gw(table)
    assert g.call_tool("u", "a", "kb.search", {})["decision"] == "allow"
    assert g.call_tool("u", "a", "erp.read", {})["decision"] == "deny"
    assert g.call_tool("u", "a", "ticket.write", {})["decision"] == "needs_approval"
    assert g.call_tool("u", "a", "ticket.write", {"approval_id": "ap-1"})["decision"] == "allow"

# --- audit
def test_audit_pseudonymises_and_verifies(table):
    g = gw(table); g.chat(Request("pat@northwind-lattice.example", "a", "travel policy"))
    assert "pat@" not in g.audit.to_siem_jsonl() and g.audit.verify()

def test_audit_tamper_detected():
    a = AuditLog(b"k"); a.append(x=1); a.append(x=2); a.records[0]["x"] = 9
    assert not a.verify()

def test_cost_math():
    assert cost("mock-large", 1_000_000, 0) == CATALOG["mock-large"].price_in
