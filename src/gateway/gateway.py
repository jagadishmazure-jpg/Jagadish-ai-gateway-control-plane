"""One control plane for model calls and MCP tool calls.

Request pipeline: identity -> safety -> PII redaction -> model allow/deny -> routing ->
budget (downgrade/block) -> cache -> provider with fallback -> audit + span."""
from dataclasses import dataclass

from .audit import AuditLog
from .budget import BudgetExceeded, Ledger
from .cache import SemanticCache
from .policy import PolicyStore
from .providers import MockProvider, cost
from .router import Router, classify_task
from .safety import classify, redact
from .telemetry import Tracer


@dataclass
class Request:
    user: str
    team: str
    prompt: str
    model: str = "auto"

class Gateway:
    def __init__(self, policies: PolicyStore, router: Router, provider: MockProvider | None = None,
                 fallback_order=("mock-medium", "mock-small", "mock-selfhosted")):
        self.policies, self.router = policies, router
        self.provider = provider or MockProvider()
        self.ledger, self.cache, self.audit, self.tracer = Ledger(), SemanticCache(), AuditLog(), Tracer()
        self.fallback_order = fallback_order

    def _deny(self, req, span, reason):
        self.audit.append(user=self.audit.pseudonym(req.user), team=req.team, kind="model", decision="deny", reason=reason)
        self.tracer.end(span, **{"gateway.decision": "deny", "gateway.reason": reason})
        return {"status": "denied", "reason": reason}

    def chat(self, req: Request) -> dict:
        span = self.tracer.span("chat", **{"gen_ai.operation.name": "chat", "enduser.team": req.team})
        try:
            pol = self.policies.get(req.team)
        except PermissionError as e:
            return self._deny(req, span, str(e))
        if cat := classify(req.prompt):
            return self._deny(req, span, f"content_safety:{cat}")
        prompt, pii = redact(req.prompt)
        task = classify_task(prompt)
        if req.model == "auto":
            model = self.router.choose(task, pol.allowed_models - pol.denied_models)
        elif not pol.model_allowed(req.model):
            return self._deny(req, span, f"model_not_allowed:{req.model}")
        else:
            model = req.model
        if hit := self.cache.get(req.team, prompt):
            self.audit.append(user=self.audit.pseudonym(req.user), team=req.team, kind="model", decision="cache_hit", model=hit["model"], pii=pii)
            self.tracer.end(span, **{"gateway.cache": "hit", "gen_ai.request.model": hit["model"]})
            return {**hit, "status": "ok", "cache": True, "pii_redacted": pii}
        try:
            model, note = self.ledger.decide(pol, model, len(prompt.split()) * 2)
        except BudgetExceeded as e:
            return self._deny(req, span, f"budget:{e}")
        tried = [model] + [m for m in self.fallback_order if m != model and pol.model_allowed(m)]
        for m in tried:
            try:
                r = self.provider.complete(m, prompt, task)
                break
            except ConnectionError:
                note = f"fallback_from:{m}"
        else:
            return self._deny(req, span, "all_providers_down")
        usd = cost(m, r["tokens_in"], r["tokens_out"])
        self.ledger.record(req.team, r["tokens_in"] + r["tokens_out"], usd)
        out = {"status": "ok", "model": m, "text": r["text"], "correct": r["correct"], "usd": usd, "note": note,
               "task": task, "cache": False, "pii_redacted": pii}
        self.cache.put(req.team, prompt, {"model": m, "text": r["text"], "correct": r["correct"], "usd": 0.0, "task": task, "note": "cache"})
        self.audit.append(user=self.audit.pseudonym(req.user), team=req.team, kind="model", decision="allow", model=m, note=note, pii=pii, usd=round(usd, 8))
        self.tracer.end(span, **{"gen_ai.request.model": m, "gen_ai.usage.input_tokens": r["tokens_in"],
                                 "gen_ai.usage.output_tokens": r["tokens_out"], "gateway.note": note})
        return out

    def call_tool(self, user: str, team: str, tool: str, args: dict) -> dict:
        """MCP tool gate: team allow-list + write tools need an approval id."""
        pol = self.policies.get(team)
        if tool not in pol.allowed_tools:
            decision = "deny"
        elif tool.endswith(".write") and not args.get("approval_id"):
            decision = "needs_approval"
        else:
            decision = "allow"
        self.audit.append(user=self.audit.pseudonym(user), team=team, kind="tool", tool=tool, decision=decision)
        return {"decision": decision}
