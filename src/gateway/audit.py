"""Tamper-evident audit log: each record carries an HMAC over (previous mac + record).
Identity fields are pseudonymised with a keyed HMAC (key from env in production)."""
import hashlib
import hmac
import json
import os


class AuditLog:
    def __init__(self, key: bytes | None = None):
        self.key = key or os.environ.get("AUDIT_HMAC_KEY", "lab-only-key").encode()
        self.records: list[dict] = []

    def pseudonym(self, user: str) -> str:
        return "u_" + hmac.new(self.key, user.encode(), hashlib.sha256).hexdigest()[:12]

    def append(self, **rec):
        prev = self.records[-1]["mac"] if self.records else ""
        body = json.dumps(rec, sort_keys=True)
        rec["mac"] = hmac.new(self.key, (prev + body).encode(), hashlib.sha256).hexdigest()
        self.records.append(rec)

    def verify(self) -> bool:
        prev = ""
        for r in self.records:
            body = json.dumps({k: v for k, v in r.items() if k != "mac"}, sort_keys=True)
            if not hmac.compare_digest(r["mac"], hmac.new(self.key, (prev + body).encode(), hashlib.sha256).hexdigest()):
                return False
            prev = r["mac"]
        return True

    def to_siem_jsonl(self) -> str:
        return "\n".join(json.dumps(r, sort_keys=True) for r in self.records)
