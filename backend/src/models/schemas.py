"""Minimal schemas — only what the tools actually use."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class FinancialMetrics(BaseModel):
    ticker: str
    current_price: Optional[float] = None
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    roe: Optional[float] = None
    revenue_growth_yoy: Optional[float] = None
    profit_margin: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    source: str = "yfinance"


class WebSearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    source_reliability: int = Field(ge=1, le=5)
