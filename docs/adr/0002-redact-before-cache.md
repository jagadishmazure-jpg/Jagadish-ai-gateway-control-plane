# ADR 0002: Redact PII before the provider and the cache
Status: accepted. Decision: redaction is the first transform after safety; the cache key and stored value are both post-redaction. Consequence: cached answers never contain the original identifiers; some cache hits are lost when two prompts differ only by PII.
