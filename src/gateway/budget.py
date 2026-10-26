"""Token ledger per team with soft-limit downgrade and hard-limit block."""
from collections import defaultdict


class BudgetExceeded(Exception):
    pass

class Ledger:
    def __init__(self):
        self.used = defaultdict(int)
        self.spend = defaultdict(float)

    def decide(self, policy, requested_model: str, est_tokens: int) -> tuple[str, str]:
        used = self.used[policy.team]
        if used + est_tokens > policy.monthly_tokens:
            raise BudgetExceeded(f"{policy.team} over monthly token budget")
        if used + est_tokens > policy.soft_limit_pct * policy.monthly_tokens and requested_model != policy.downgrade_to:
            return policy.downgrade_to, "downgraded:soft_budget"
        return requested_model, "ok"

    def record(self, team: str, tokens: int, usd: float):
        self.used[team] += tokens
        self.spend[team] += usd
