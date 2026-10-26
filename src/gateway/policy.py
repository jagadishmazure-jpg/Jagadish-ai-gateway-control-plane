"""Per-team policy: model allow/deny, MCP tool allow-list, token budgets, downgrade path."""
from dataclasses import dataclass, field


@dataclass
class TeamPolicy:
    team: str
    allowed_models: set[str]
    denied_models: set[str] = field(default_factory=set)
    allowed_tools: set[str] = field(default_factory=set)
    monthly_tokens: int = 100_000
    soft_limit_pct: float = 0.8           # above this, downgrade to the cheaper model
    downgrade_to: str = "mock-small"

    def model_allowed(self, model: str) -> bool:
        return model in self.allowed_models and model not in self.denied_models

class PolicyStore:
    """Runtime-editable: changes apply to the next request (no redeploy)."""
    def __init__(self, policies: list[TeamPolicy]):
        self._p = {p.team: p for p in policies}

    def get(self, team: str) -> TeamPolicy:
        if team not in self._p:
            raise PermissionError(f"unknown team {team!r}")
        return self._p[team]

    def deny_model(self, team: str, model: str):
        self.get(team).denied_models.add(model)

    def allow_model(self, team: str, model: str):
        p = self.get(team); p.denied_models.discard(model); p.allowed_models.add(model)
