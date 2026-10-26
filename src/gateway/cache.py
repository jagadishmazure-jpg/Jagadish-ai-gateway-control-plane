"""Semantic cache using hashed bag-of-words vectors + cosine similarity (offline stand-in for embeddings).

Scoped per team so one team's cached answer is never served to another.
"""
import math, re, hashlib

DIM = 512
STOP = {"the", "a", "an", "is", "of", "to", "for", "what", "how", "do", "i", "my", "please", "can", "you"}

def embed(text: str) -> list[float]:
    v = [0.0] * DIM
    for w in re.findall(r"[a-z0-9]+", text.lower()):
        if w in STOP:
            continue
        v[int(hashlib.md5(w.encode()).hexdigest(), 16) % DIM] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]

def cosine(a, b):
    return sum(x * y for x, y in zip(a, b))

class SemanticCache:
    def __init__(self, threshold: float = 0.9):
        self.threshold = threshold
        self.entries: list[tuple[str, list[float], str, dict]] = []

    def get(self, team: str, prompt: str):
        q = embed(prompt)
        best = max(((cosine(q, e), r) for t, e, _, r in self.entries if t == team), default=(0, None), key=lambda x: x[0])
        return best[1] if best[0] >= self.threshold else None

    def put(self, team: str, prompt: str, response: dict):
        self.entries.append((team, embed(prompt), prompt, response))
