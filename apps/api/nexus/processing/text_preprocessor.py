"""Text preprocessing utilities for NER input."""

import re
from typing import Any


def clean_text(text: str) -> str:
    """Clean and normalize text for NER processing."""
    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    # Remove null bytes
    text = text.replace("\x00", "")
    # Normalize unicode
    text = text.strip()
    return text


def segment_sentences(text: str) -> list[str]:
    """Split text into sentences using simple rules."""
    # Split on period, exclamation, question mark followed by space or end
    sentences = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sentences if s.strip()]


def extract_text_from_collection_result(result: dict[str, Any]) -> str:
    """Extract processable text from a collection result's normalized data."""
    parts: list[str] = []

    for key in ["content", "text", "description", "summary", "body", "banner", "name"]:
        value = result.get(key)
        if isinstance(value, str) and value:
            parts.append(value)

    # Flatten lists of strings
    for key in ["hostnames", "subdomains", "emails", "detection_names"]:
        value = result.get(key)
        if isinstance(value, list):
            parts.extend(str(v) for v in value if v)

    return " ".join(parts)
