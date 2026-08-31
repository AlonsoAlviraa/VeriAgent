"""Log sanitizer: never print full hashes, NIFs, PEMs, or Authorization."""

from __future__ import annotations

import re
from typing import Optional

_PEM_RE = re.compile(
    r"-----BEGIN [^-]+-----.*?-----END [^-]+-----",
    re.DOTALL | re.IGNORECASE,
)
_AUTH_RE = re.compile(
    r"(?i)\bauthorization\s*[:=]\s*(?:bearer\s+)?\S+",
)
_KEY_ASSIGN_RE = re.compile(
    r"(?i)\b(?:key|token|api[_-]?key)=[^\s&]+",
)
_HEX64_RE = re.compile(r"\b[A-Fa-f0-9]{64}\b")
_NIF_RE = re.compile(r"\b[A-Z]\d{7}[A-Z0-9]\b", re.IGNORECASE)
_CERT_PATH_RE = re.compile(
    r"(?i)(?:^|[\s=\"'])(\S+\.(?:pem|p12|pfx|key))\b",
)


def redact_secret(value: Optional[str], *, keep: int = 8) -> str:
    """Mask a secret as first8…last8. Short values are omitted entirely."""
    if value is None:
        return ""
    text = str(value)
    if not text:
        return ""
    if len(text) <= keep * 2:
        return "[omitted]"
    return f"{text[:keep]}…{text[-keep:]}"


def sanitize_log(text: Optional[str]) -> str:
    """Drop or mask material that must not appear in logs."""
    if text is None:
        return ""
    out = str(text)
    out = _PEM_RE.sub("[omitted-pem]", out)
    out = _AUTH_RE.sub("[omitted-auth]", out)
    out = _KEY_ASSIGN_RE.sub("[redacted]", out)
    out = _HEX64_RE.sub(lambda m: redact_secret(m.group(0)), out)
    out = _NIF_RE.sub("[REDACTED_NIF]", out)

    def _path(match: re.Match) -> str:
        prefix = match.group(0)[: match.start(1) - match.start(0)]
        return f"{prefix}[omitted-cert-path]"

    out = _CERT_PATH_RE.sub(_path, out)
    return out
