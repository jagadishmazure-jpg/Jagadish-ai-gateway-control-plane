"""Offline mock model providers. Deterministic, no network, no billing.

Prices are ILLUSTRATIVE lab values (USD per 1M tokens), not vendor quotes.
"""
import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Model:
    name: str
    tier: str            # "small" | "medium" | "large"
    price_in: float      # illustrative USD / 1M input tokens
    price_out: float     # illustrative USD / 1M output tokens
    skill: dict          # task -> probability of a correct answer (synthetic)

CATALOG = {
    "mock-small": Model("mock-small", "small", 0.15, 0.60, {"faq": 0.93, "extract": 0.88, "reason": 0.55, "code": 0.60}),
    "mock-medium": Model("mock-medium", "medium", 0.80, 3.20, {"faq": 0.95, "extract": 0.93, "reason": 0.78, "code": 0.80}),
    "mock-large": Model("mock-large", "large", 3.00, 12.00, {"faq": 0.96, "extract": 0.95, "reason": 0.90, "code": 0.91}),
    "mock-selfhosted": Model("mock-selfhosted", "medium", 0.0, 0.0, {"faq": 0.92, "extract": 0.90, "reason": 0.70, "code": 0.74}),
}

def count_tokens(text: str) -> int:
    """Rough whitespace tokenizer (documented approximation)."""
    return max(1, len(text.split()))

def _u(*parts) -> float:
    h = hashlib.sha256("|".join(map(str, parts)).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF

class MockProvider:
    """Answers deterministically; correctness drawn from the model's synthetic skill table."""
    def __init__(self, fail_models: set[str] | None = None):
        self.fail_models = fail_models or set()

    def complete(self, model: str, prompt: str, task: str = "faq") -> dict:
        if model in self.fail_models:
            raise ConnectionError(f"{model} unavailable")
        m = CATALOG[model]
        correct = _u(model, prompt) < m.skill.get(task, 0.5)
        out = f"[{model}] answer to: {prompt[:40]}"
        return {"text": out, "correct": correct, "tokens_in": count_tokens(prompt), "tokens_out": count_tokens(out)}

def cost(model: str, tin: int, tout: int) -> float:
    m = CATALOG[model]
    return (tin * m.price_in + tout * m.price_out) / 1_000_000
