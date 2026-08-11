"""
Unit & Integration Test Suite for AI Data Ingestion & Entity Resolution Pipeline.
"""

import sys
import os
import pytest
from datetime import datetime, timezone, timedelta

# Ensure src module resolution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.llm.schemas import StartupEntity, ProductEntity, ResearchPaperEntity, JobEntity, NewsEntity
from src.llm.chunker import IntelligentChunker
from src.llm.orchestrator import LLMOrchestrator
from src.resolver.entity_resolver import EntityResolver
from src.crawlers.utils import parse_and_normalize_date, is_within_last_24_hours


def test_intelligent_chunker():
    chunker = IntelligentChunker(max_chunk_chars=100, overlap_chars=10)
    raw_html = "<html><head><script>var x=10;</script></head><body><h1>Title</h1><p>This is a long paragraph content for testing cleaning and chunking.</p></body></html>"
    
    clean_text = chunker.clean_html(raw_html)
    assert "script" not in clean_text.lower()
    assert "Title" in clean_text
    assert "paragraph" in clean_text

    chunks = chunker.chunk_text(clean_text)
    assert len(chunks) >= 1
    for c in chunks:
        assert len(c) <= 100


def test_date_parser_and_24h_freshness():
    now = datetime.now(timezone.utc)
    
    # Relative date testing
    dt_2h = parse_and_normalize_date("2 hours ago")
    assert dt_2h is not None
    assert is_within_last_24_hours(dt_2h) is True

    dt_3d = parse_and_normalize_date("3 days ago")
    assert dt_3d is not None
    assert is_within_last_24_hours(dt_3d) is False

    # ISO string testing
    iso_str = now.isoformat()
    dt_iso = parse_and_normalize_date(iso_str)
    assert dt_iso is not None
    assert is_within_last_24_hours(dt_iso) is True


def test_entity_resolver():
    resolver = EntityResolver()

    # Exact alias test
    assert resolver.resolve("Open AI") == "OpenAI"
    assert resolver.resolve("OpenAI, Inc.") == "OpenAI"
    assert resolver.resolve("deepmind") == "Google DeepMind"
    assert resolver.resolve("huggingface inc") == "Hugging Face"

    # Fuzzy match test
    assert resolver.resolve("Anthropic PBC") == "Anthropic"
    assert resolver.resolve("Perplexity AI Inc") == "Perplexity AI"

    # Check logs
    logs = resolver.get_logs()
    assert len(logs) >= 6
    assert any(log.raw_name == "Open AI" and log.canonical_name == "OpenAI" for log in logs)


@pytest.mark.asyncio
async def test_llm_orchestrator_fallback():
    orchestrator = LLMOrchestrator()
    # Force fallback tier execution
    validated = await orchestrator.extract_structured("Extract startup metadata", "Test startup text", StartupEntity)
    assert validated.recordType == "STARTUP"
    assert validated.schemaVersion == "1.0"
    assert validated.content.entityName is not None
