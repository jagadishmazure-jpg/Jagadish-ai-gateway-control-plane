"""Minimal span recorder shaped after the OpenTelemetry GenAI semantic conventions
(gen_ai.* attribute names). Exports JSONL offline; swap for the OTel SDK in production."""
import time, uuid

class Tracer:
    def __init__(self):
        self.spans: list[dict] = []

    def span(self, name: str, **attrs):
        s = {"trace_id": uuid.uuid4().hex, "name": name, "start": time.time(), "attributes": dict(attrs)}
        self.spans.append(s)
        return s

    def end(self, s: dict, **attrs):
        s["attributes"].update(attrs)
        s["duration_ms"] = round((time.time() - s["start"]) * 1000, 3)
