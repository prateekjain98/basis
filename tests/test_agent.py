"""
Tests for tool reliability and pipeline components.
Does NOT test the LLM synthesis step (requires real API key).
"""

from __future__ import annotations

import os
import sys
import uuid

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from src.tools.web_search import WebSearchTool
from src.tools.stock_scorer import StockScorer
from src.tools.vector_store import SessionVectorStore
from src.tools.document_fetcher import DocumentFetcher
from src.models.schemas import FinancialMetrics


def test_web_search_returns_results():
    tool = WebSearchTool()
    results = tool.run("Apple stock analysis", max_results=3)
    assert isinstance(results, list)
    assert len(results) <= 3


def test_web_search_graceful_on_total_failure():
    tool = WebSearchTool()
    results = tool.run("xyzfake12345noresults", max_results=3)
    assert isinstance(results, list)


def test_stock_scorer_returns_partial_on_failure():
    scorer = StockScorer()
    result = scorer.score("FAKE_TICKER_123")
    assert isinstance(result["metrics"], FinancialMetrics)
    assert result["metrics"].ticker == "FAKE_TICKER_123"
    assert result["metrics"].current_price is None


def test_stock_scorer_populates_known_ticker():
    scorer = StockScorer()
    result = scorer.score("AAPL")
    assert isinstance(result["metrics"], FinancialMetrics)
    assert result["metrics"].ticker == "AAPL"
    assert result["metrics"].source == "yfinance"


def test_vector_store_lifecycle():
    import pytest
    from src.config import settings
    if not settings.openai_api_key or "dummy" in settings.openai_api_key.lower():
        pytest.skip("No real OpenAI key — embedding requires it")

    store = SessionVectorStore()
    session_id = str(uuid.uuid4())

    # Index
    count = store.index_documents(session_id, ["Apple is a technology company.", "NVIDIA makes GPUs."])
    assert count > 0

    # Query
    chunks = store.query(session_id, "technology", top_k=2)
    assert isinstance(chunks, list)
    assert len(chunks) <= 2

    # Delete
    store.delete_session(session_id)
    chunks_after = store.query(session_id, "technology", top_k=2)
    assert chunks_after == []


def test_document_fetcher_finds_pdfs():
    fetcher = DocumentFetcher()
    docs = fetcher.find_and_download("renewable energy investment", top_n=2)
    assert isinstance(docs, list)
    for d in docs:
        assert "path" in d
        assert "url" in d
        assert "title" in d
        assert os.path.exists(d["path"])
        assert d["score"] > 0


def test_document_fetcher_scoring():
    fetcher = DocumentFetcher()
    # Test the scoring logic directly
    from src.tools.document_fetcher import Candidate

    c = Candidate(url="https://sec.gov/filing.pdf", title="SEC Filing 2025", source_query="test")
    c.domain_score = 3.0
    c.url_score = 0.5
    c.title_score = 0.8
    c.valid_pdf = True
    c.parse_score = 0.9
    c.compute_final()
    assert c.final_score > 0
