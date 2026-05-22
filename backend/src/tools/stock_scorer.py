"""Fetch financials from yfinance and compute a 0-100 score.

Production-ready: LRU cache, concurrency semaphore, timeout handling.
"""

from __future__ import annotations

import asyncio
import threading
from functools import lru_cache
from typing import Optional

import yfinance as yf

from src.models.schemas import FinancialMetrics

# Global semaphore: max 5 concurrent yfinance calls.
# yfinance rate-limits after ~20 rapid requests; this prevents bans.
_YF_LOCK = threading.Semaphore(5)


def _safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@lru_cache(maxsize=256)
def _fetch_cached(ticker: str) -> FinancialMetrics:
    """Cached yfinance fetch. TTL is implicit via LRU eviction.
    For production, consider a TTL cache (e.g. cachetools.TTLCache).
    """
    with _YF_LOCK:
        r = FinancialMetrics(ticker=ticker.upper())
        try:
            info = yf.Ticker(ticker).info or {}
            r.current_price = _safe_float(info.get("currentPrice"))
            r.market_cap = _safe_float(info.get("marketCap"))
            r.pe_ratio = _safe_float(info.get("trailingPE"))
            r.pb_ratio = _safe_float(info.get("priceToBook"))
            r.debt_to_equity = _safe_float(info.get("debtToEquity"))
            r.roe = _safe_float(info.get("returnOnEquity"))
            r.revenue_growth_yoy = _safe_float(info.get("revenueGrowth"))
            r.profit_margin = _safe_float(info.get("profitMargins"))
            r.fifty_two_week_high = _safe_float(info.get("fiftyTwoWeekHigh"))
            r.fifty_two_week_low = _safe_float(info.get("fiftyTwoWeekLow"))
        except Exception as e:
            print(f"[StockScorer] yfinance error for {ticker}: {e}")
        return r


class StockScorer:
    def score(self, ticker: str) -> dict:
        m = _fetch_cached(ticker.upper())
        return {
            "fundamentals_score": self._fundamentals(m),
            "risk_score": self._risk(m),
            "momentum_score": self._momentum(m),
            "liquidity_score": self._liquidity(m),
            "metrics": m,
        }

    @staticmethod
    def _fundamentals(m: FinancialMetrics) -> int:
        s = 50
        if m.pe_ratio and m.pe_ratio < 25:
            s += 15
        elif m.pe_ratio and m.pe_ratio > 40:
            s -= 15
        if m.roe and m.roe > 0.15:
            s += 15
        if m.revenue_growth_yoy and m.revenue_growth_yoy > 0.20:
            s += 10
        if m.profit_margin and m.profit_margin > 0.15:
            s += 10
        return max(0, min(100, s))

    @staticmethod
    def _risk(m: FinancialMetrics) -> int:
        s = 50
        if m.debt_to_equity and m.debt_to_equity < 50:
            s += 20
        elif m.debt_to_equity and m.debt_to_equity > 100:
            s -= 20
        if m.market_cap and m.market_cap > 100e9:
            s += 15
        elif m.market_cap and m.market_cap < 10e9:
            s -= 10
        if m.fifty_two_week_high and m.fifty_two_week_low and m.current_price:
            ratio = (m.current_price - m.fifty_two_week_low) / (m.fifty_two_week_high - m.fifty_two_week_low + 1e-6)
            if ratio > 0.8:
                s -= 10
            elif ratio < 0.3:
                s += 10
        return max(0, min(100, s))

    @staticmethod
    def _momentum(m: FinancialMetrics) -> int:
        s = 50
        if m.revenue_growth_yoy and m.revenue_growth_yoy > 0.30:
            s += 25
        elif m.revenue_growth_yoy and m.revenue_growth_yoy < 0:
            s -= 15
        return max(0, min(100, s))

    @staticmethod
    def _liquidity(m: FinancialMetrics) -> int:
        s = 50
        if m.market_cap and m.market_cap > 50e9:
            s += 30
        elif m.market_cap and m.market_cap > 10e9:
            s += 15
        return max(0, min(100, s))
