"""Typed Pydantic models for Supabase tables.

These are NOT SQLAlchemy models — we use Supabase's REST API.
These types give us autocomplete and validation when working with rows.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ThesisSession(BaseModel):
    id: str
    user_query: str
    theme: Optional[str] = None
    summary: Optional[str] = None
    conviction: Optional[str] = None  # "High" | "Medium" | "Low"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Document(BaseModel):
    id: str
    thesis_id: str
    url: str
    title: Optional[str] = None
    source: Optional[str] = None
    parsed_content: Optional[str] = None
    chunk_count: int = 0
    created_at: Optional[datetime] = None


class StockRecommendation(BaseModel):
    id: str
    thesis_id: str
    ticker: str
    name: Optional[str] = None
    entry_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    position_size: Optional[str] = None
    fundamentals_score: Optional[float] = None
    thematic_fit_score: Optional[float] = None
    risk_score: Optional[float] = None
    momentum_score: Optional[float] = None
    liquidity_score: Optional[float] = None
    total_score: Optional[float] = None
    rationale: Optional[str] = None
    created_at: Optional[datetime] = None


class Message(BaseModel):
    id: str
    session_id: str
    role: str  # "user" | "assistant"
    content: str
    created_at: Optional[datetime] = None
