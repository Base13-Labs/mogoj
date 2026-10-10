"""Secret detection and safe redaction for local memory writes."""

import re


SECRET_PATTERNS = (
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("GitHub token", re.compile(r"\b(?:gh[psour]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("OpenAI key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("AWS access key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("Slack token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("credential assignment", re.compile(
        r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*['\"]?([^\s'\"]{8,})"
    )),
)


def detect_secrets(text):
    """Return pattern labels only; never return matched secret material."""
    return sorted({name for name, pattern in SECRET_PATTERNS if pattern.search(text)})


def redact_secrets(text):
    """Replace secret-looking values without retaining them in output."""
    redacted = text
    for name, pattern in SECRET_PATTERNS:
        replacement = f"[REDACTED {name.upper()}]"
        if name == "credential assignment":
            redacted = pattern.sub(lambda match: match.group(0).replace(match.group(1), replacement), redacted)
        else:
            redacted = pattern.sub(replacement, redacted)
    return redacted
