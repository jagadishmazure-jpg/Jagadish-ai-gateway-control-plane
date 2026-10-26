"""Input/output guards: PII redaction (with Luhn check for cards) and a content-safety category filter."""
import re

EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")
PHONE = re.compile(r"\b(?:\+1[ -]?)?\(?\d{3}\)?[ -]?\d{3}-\d{4}\b")
SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
CARD = re.compile(r"\b(?:\d[ -]?){13,16}\b")

def luhn_ok(num: str) -> bool:
    d = [int(c) for c in re.sub(r"\D", "", num)][::-1]
    s = sum(d[0::2]) + sum(sum(divmod(2 * x, 10)) for x in d[1::2])
    return len(d) >= 13 and s % 10 == 0

def redact(text: str) -> tuple[str, list[str]]:
    found = []
    def sub(kind):
        def f(m):
            found.append(kind)
            return f"[{kind}]"
        return f
    text = SSN.sub(sub("SSN"), text)
    text = CARD.sub(lambda m: (found.append("CARD") or "[CARD]") if luhn_ok(m.group()) else m.group(), text)
    text = EMAIL.sub(sub("EMAIL"), text)
    text = PHONE.sub(sub("PHONE"), text)
    return text, found

BLOCKED = {
    "violence": ["build a weapon", "make a bomb", "hurt someone"],
    "self_harm": ["kill myself", "end my life"],
    "malware": ["write ransomware", "keylogger that hides"],
}

def classify(text: str) -> str | None:
    t = text.lower()
    for cat, phrases in BLOCKED.items():
        if any(p in t for p in phrases):
            return cat
    return None
