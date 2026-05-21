"""
Pydantic schemas for the Portfolio Research Agent.
Every LLM output is typed. No free-text soup.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class ConvictionLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class ResearchPrompt(BaseModel):
    """What the user asks for."""

    query: str = Field(description="The user's research question")
    ticker: Optional[str] = Field(
        default=None, description="Optional ticker symbol if known"
    )
    follow_up: bool = Field(
        default=False,
        description="Whether this is a follow-up in an existing session",
    )


class FinancialMetrics(BaseModel):
    """Key financial data pulled for a company."""

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
    """A single web search result."""

    title: str
    url: str
    snippet: str
    source_reliability: int = Field(
        ge=1, le=5, description="Subjective reliability score (1=blog, 5=SEC filing)"
    )


class ResearchContext(BaseModel):
    """All data collected so far in the session."""

    financials: Optional[FinancialMetrics] = None
    web_results: List[WebSearchResult] = Field(default_factory=list)
    notes: List[str] = Field(
        default_factory=list,
        description="Raw observations the agent has made",
    )


class InvestmentThesis(BaseModel):
    """The final structured output — the whole point."""

    company_or_theme: str
    executive_summary: str = Field(
        max_length=500,
        description="2-3 sentence elevator pitch for the thesis",
    )
    investment_rationale: List[str] = Field(
        min_length=1,
        max_length=5,
        description="Bulleted bull-case points grounded in data",
    )
    key_risks: List[str] = Field(
        min_length=1,
        max_length=5,
        description="Bear-case risks that could invalidate the thesis",
    )
    conviction: ConvictionLevel
    target_price_range: Optional[str] = Field(
        default=None,
        description="E.g., 'INR 850-950' with brief justification",
    )
    data_sources_used: List[str] = Field(
        default_factory=list,
        description="Which tools/data informed this thesis",
    )


class AgentStep(BaseModel):
    """One turn in the agent's internal loop."""

    step_number: int
    thought: str = Field(description="What the agent planned to do")
    action: str = Field(description="Which tool was invoked")
    observation: str = Field(description="What the tool returned")


class SessionState(BaseModel):
    """Full session memory — persisted across turns."""

    session_id: str
    original_prompt: ResearchPrompt
    context: ResearchContext = Field(default_factory=ResearchContext)
    steps: List[AgentStep] = Field(default_factory=list)
    latest_thesis: Optional[InvestmentThesis] = None
    completed: bool = False
