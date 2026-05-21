"""
Main Agent Orchestrator

Explicit state machine per turn:
    PLAN → TOOL_CALL → OBSERVE → SYNTHESIZE

No hidden loops. Every action is logged.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from dotenv import load_dotenv

from src.memory.session import get_session_manager
from src.models.schemas import (
    AgentStep,
    FinancialMetrics,
    InvestmentThesis,
    ResearchContext,
    ResearchPrompt,
    SessionState,
    WebSearchResult,
)
from src.tools.financial_data import FinancialDataTool
from src.tools.thesis_builder import ThesisBuilderTool
from src.tools.web_search import WebSearchTool

load_dotenv()


class ResearchAgent:
    """
    Multi-step research agent.

    Walkthrough of one full turn:
        1. Parse user input into ResearchPrompt
        2. Load or create session
        3. Plan: decide which tools to call
        4. Execute: run financial data + web search in parallel
        5. Observe: collect results into ResearchContext
        6. Synthesize: call thesis builder → structured output
        7. Save: update session state
    """

    def __init__(self) -> None:
        self.financial_tool = FinancialDataTool()
        self.web_tool = WebSearchTool()
        self.thesis_tool = ThesisBuilderTool()
        self.sessions = get_session_manager()

    def run(
        self, query: str, ticker: str | None = None, session_id: str | None = None
    ) -> InvestmentThesis:
        """
        Entry point — run one research cycle.

        Args:
            query: What to research (e.g., "Bull case for Tata Motors")
            ticker: Optional ticker symbol for financial data lookup
            session_id: For follow-ups — continues existing session

        Returns:
            InvestmentThesis: structured thesis output
        """
        # ── 1. Parse ──────────────────────────────────────────────
        prompt = ResearchPrompt(query=query, ticker=ticker)

        # ── 2. Session ────────────────────────────────────────────
        if session_id and self.sessions.get_session(session_id):
            state = self.sessions.get_session(session_id)
            prompt.follow_up = True
            print(f"[Session] Continuing session {session_id}")
        else:
            session_id = self.sessions.create_session(prompt)
            state = self.sessions.get_session(session_id)
            print(f"[Session] Created new session {session_id}")

        # ── 3. Plan ───────────────────────────────────────────────
        step_num = len(state.steps) + 1
        plan = self._plan(state, prompt)
        print(f"[Plan] {plan}")

        # ── 4. Execute tools ──────────────────────────────────────
        financials: FinancialMetrics | None = None
        web_results: list[WebSearchResult] = []

        if "financial_data" in plan and prompt.ticker:
            print(f"[Tool] Fetching financials for {prompt.ticker}...")
            financials = self.financial_tool.run(prompt.ticker)
            state.steps.append(
                AgentStep(
                    step_number=step_num,
                    thought=f"Need financial data for {prompt.ticker}",
                    action="financial_data",
                    observation=json.dumps(
                        financials.model_dump(exclude_none=True), indent=2
                    )[:500],
                )
            )
            state.context.financials = financials

        if "web_search" in plan:
            search_query = self._build_search_query(prompt, state)
            print(f"[Tool] Searching web: '{search_query}'...")
            web_results = self.web_tool.run(search_query, max_results=5)
            state.steps.append(
                AgentStep(
                    step_number=step_num + 1,
                    thought="Need recent news and context",
                    action="web_search",
                    observation=f"Retrieved {len(web_results)} results",
                )
            )
            state.context.web_results = web_results

        # ── 5. Synthesize ─────────────────────────────────────────
        print("[Tool] Building thesis...")
        thesis = self.thesis_tool.run(
            query=prompt.query,
            financials=financials,
            web_results=web_results,
        )
        state.latest_thesis = thesis
        state.completed = True

        # ── 6. Save ───────────────────────────────────────────────
        self.sessions.update_session(session_id, state)
        print(f"[Session] Saved. Session ID: {session_id}")

        return thesis

    def follow_up(self, session_id: str, new_query: str) -> InvestmentThesis:
        """
        Continue an existing session with a follow-up question.

        The new query is combined with existing context so the agent
        knows what was already researched.
        """
        state = self.sessions.get_session(session_id)
        if not state:
            raise ValueError(f"Session {session_id} not found")

        # Build enriched query with prior context
        enriched_query = (
            f"Previous research: {state.original_prompt.query}\n"
            f"Current thesis: {state.latest_thesis.executive_summary if state.latest_thesis else 'N/A'}\n"
            f"Follow-up: {new_query}"
        )

        return self.run(
            query=enriched_query,
            ticker=state.original_prompt.ticker,
            session_id=session_id,
        )

    # ── Internal helpers ──────────────────────────────────────────

    def _plan(self, state: SessionState, prompt: ResearchPrompt) -> list[str]:
        """
        Decide which tools to invoke.

        Simple rule-based planner for reliability.
        Could be replaced with an LLM planner for more complex tasks.
        """
        tools = []

        # Always search the web for context
        tools.append("web_search")

        # If we have a ticker, get financials
        if prompt.ticker:
            tools.append("financial_data")

        return tools

    def _build_search_query(
        self, prompt: ResearchPrompt, state: SessionState
    ) -> str:
        """Construct an effective web search query from the prompt."""
        parts = [prompt.query]
        if prompt.ticker:
            parts.append(prompt.ticker)
        # Add current year for recency
        parts.append("2025 2026")
        return " ".join(parts)


def main() -> None:
    """CLI entry point for quick testing."""
    parser = argparse.ArgumentParser(
        description="Portfolio Research Agent — CLI"
    )
    parser.add_argument("query", help="Research question or company name")
    parser.add_argument("--ticker", "-t", help="Stock ticker symbol")
    parser.add_argument(
        "--session", "-s", help="Session ID for follow-up questions"
    )
    parser.add_argument(
        "--follow-up", "-f", help="Follow-up question (requires --session)"
    )
    args = parser.parse_args()

    agent = ResearchAgent()

    if args.follow_up:
        if not args.session:
            print("Error: --follow-up requires --session")
            sys.exit(1)
        result = agent.follow_up(args.session, args.follow_up)
    else:
        result = agent.run(args.query, ticker=args.ticker)

    # Pretty print the thesis
    print("\n" + "=" * 60)
    print(f"  INVESTMENT THESIS: {result.company_or_theme}")
    print("=" * 60)
    print(f"\nExecutive Summary:\n  {result.executive_summary}\n")
    print(f"Conviction: {result.conviction.value}")
    if result.target_price_range:
        print(f"Target Price Range: {result.target_price_range}")
    print("\nInvestment Rationale:")
    for i, point in enumerate(result.investment_rationale, 1):
        print(f"  {i}. {point}")
    print("\nKey Risks:")
    for i, risk in enumerate(result.key_risks, 1):
        print(f"  {i}. {risk}")
    print(f"\nSources: {', '.join(result.data_sources_used)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
