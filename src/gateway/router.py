"""Eval-informed routing: for each task type, choose the cheapest allowed model whose
measured accuracy on the offline eval set is within `tolerance` of the best model."""
from .providers import CATALOG, MockProvider

def run_evals(eval_set: list[dict], provider: MockProvider) -> dict:
    """Returns {task: {model: accuracy}} measured on the eval set."""
    table: dict = {}
    for task in sorted({e["task"] for e in eval_set}):
        items = [e for e in eval_set if e["task"] == task]
        table[task] = {}
        for m in CATALOG:
            ok = sum(provider.complete(m, e["prompt"], task)["correct"] for e in items)
            table[task][m] = round(ok / len(items), 4)
    return table

def classify_task(prompt: str) -> str:
    p = prompt.lower()
    if any(k in p for k in ("def ", "function", "python", "sql", "bug")):
        return "code"
    if any(k in p for k in ("extract", "invoice number", "field")):
        return "extract"
    if any(k in p for k in ("why", "plan", "compare", "trade-off")):
        return "reason"
    return "faq"

class Router:
    def __init__(self, eval_table: dict, tolerance: float = 0.03):
        self.t, self.tol = eval_table, tolerance

    def choose(self, task: str, allowed: set[str]) -> str:
        scores = {m: a for m, a in self.t.get(task, {}).items() if m in allowed}
        if not scores:
            raise PermissionError("no allowed model for task")
        best = max(scores.values())
        ok = [m for m, a in scores.items() if a >= best - self.tol]
        return min(ok, key=lambda m: (CATALOG[m].price_in + CATALOG[m].price_out, m))
