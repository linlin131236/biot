"""Conservative evidence redaction. Replaces known secret patterns with [已脱敏].
Never executes, never writes files, never calls external services.
"""
from __future__ import annotations

import re

_REDACTED = "[已脱敏]"

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"OPENAI_API_KEY\s*=\s*\S+", re.IGNORECASE), f"OPENAI_API_KEY={_REDACTED}"),
    (re.compile(r"API_KEY\s*=\s*\S+", re.IGNORECASE), f"API_KEY={_REDACTED}"),
    (re.compile(r"TOKEN\s*=\s*\S+", re.IGNORECASE), f"TOKEN={_REDACTED}"),
    (re.compile(r"SECRET\s*=\s*\S+", re.IGNORECASE), f"SECRET={_REDACTED}"),
    (re.compile(r"PASSWORD\s*=\s*\S+", re.IGNORECASE), f"PASSWORD={_REDACTED}"),
    (re.compile(r"Bearer\s+\S+"), f"Bearer {_REDACTED}"),
    (re.compile(r"\bsk-[A-Za-z0-9\-_]{15,}\b"), f"sk-{_REDACTED}"),
    (re.compile(r"-----BEGIN PRIVATE KEY-----.*?-----END PRIVATE KEY-----", re.DOTALL), "[已脱敏：私钥]"),
    (re.compile(r"-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----", re.DOTALL), "[已脱敏：证书]"),
]


def redact(text: str) -> str:
    """Apply all redaction patterns to text. Returns redacted string."""
    if not text:
        return text
    result = text
    for pattern, replacement in _PATTERNS:
        result = pattern.sub(replacement, result)
    return result
