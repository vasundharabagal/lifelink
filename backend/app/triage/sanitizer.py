"""Citizen input sanitization and PII scrubbing module (Spec §5.2, D-45).

Strips control characters, HTML/XML tags, normalizes whitespace,
clamps text to 500 characters, and removes phone numbers and email addresses.
"""
import re
import unicodedata
from typing import Optional

# Regex pattern for phone numbers (domestic, international, hyphenated, space-separated)
_PHONE_PATTERN = re.compile(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b')
# Regex pattern for standard email addresses
_EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
# HTML/XML tag stripper
_HTML_TAG_PATTERN = re.compile(r'<[^<]+?>')


def sanitize_description(text: Optional[str], max_length: int = 500) -> str:
    """Sanitize free-text emergency description.
    
    1. Redacts phone numbers and email addresses (zero PII in prompt payload).
    2. Strips HTML and XML tags to prevent tag-injection in downstream prompts.
    3. Normalizes unicode characters and removes non-printable control characters.
    4. Clamps the string to `max_length` (default 500 characters).
    5. Normalizes consecutive whitespace.
    """
    if not text:
        return ""

    # Normalize unicode to NFKC
    cleaned = unicodedata.normalize("NFKC", str(text))

    # Strip HTML and XML tags
    cleaned = _HTML_TAG_PATTERN.sub(" ", cleaned)

    # Redact email addresses
    cleaned = _EMAIL_PATTERN.sub("[REDACTED]", cleaned)

    # Redact phone numbers (minimum 8 digits in sequence/separators)
    cleaned = _PHONE_PATTERN.sub("[REDACTED]", cleaned)

    # Strip control characters except newline and tab
    cleaned = "".join(ch for ch in cleaned if unicodedata.category(ch)[0] != "C" or ch in " \t\n\r")

    # Normalize consecutive whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # Enforce strict length cap
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip()

    return cleaned
