"""NER pipeline tests."""

import pytest
from nexus.processing.ner import NERPipeline


def test_tier3_ipv4_extraction():
    """Test IPv4 address extraction from text."""
    pipeline = NERPipeline()
    text = "The server at 192.168.1.1 was communicating with 10.0.0.5"
    entities = pipeline.extract(text)

    ip_entities = [e for e in entities if e.label == "IPAddress"]
    ip_texts = {e.text for e in ip_entities}
    assert "192.168.1.1" in ip_texts
    assert "10.0.0.5" in ip_texts


def test_tier3_email_extraction():
    """Test email extraction."""
    pipeline = NERPipeline()
    text = "Contact admin@example.com for details"
    entities = pipeline.extract(text)

    emails = [e for e in entities if e.label == "Email"]
    assert any(e.text == "admin@example.com" for e in emails)


def test_tier3_cve_extraction():
    """Test CVE ID extraction."""
    pipeline = NERPipeline()
    text = "The vulnerability CVE-2024-12345 affects the system"
    entities = pipeline.extract(text)

    cves = [e for e in entities if e.label == "Vulnerability"]
    assert any(e.text == "CVE-2024-12345" for e in cves)


def test_tier3_hash_extraction():
    """Test hash extraction (SHA256)."""
    pipeline = NERPipeline()
    sha256 = "a" * 64
    text = f"File hash: {sha256}"
    entities = pipeline.extract(text)

    hashes = [e for e in entities if e.label == "Hash"]
    assert any(e.text == sha256 for e in hashes)


def test_deduplication():
    """Test that overlapping entities are deduplicated."""
    pipeline = NERPipeline()
    text = "IP 192.168.1.1 appears twice: 192.168.1.1"
    entities = pipeline.extract(text)

    # Both should be detected (at different positions)
    ip_entities = [e for e in entities if e.label == "IPAddress"]
    assert len(ip_entities) == 2


def test_confidence_scores():
    """Test that regex patterns have high confidence."""
    pipeline = NERPipeline()
    text = "Check CVE-2025-99999"
    entities = pipeline.extract(text)

    cves = [e for e in entities if e.label == "Vulnerability"]
    assert all(e.confidence == 0.95 for e in cves)
    assert all(e.tier == 3 for e in cves)
