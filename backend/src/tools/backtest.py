"""Backtest stock recommendations against historical prices.

Validates agent recommendations by comparing against:
1. Aschenbrenner's actual known holdings
2. Historical performance since fund launch (Sept 2024)
3. Entry/exit timing
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

import yfinance as yf


# Aschenbrenner's Situational Awareness LP — known long holdings from 13F filings
# Source: SEC 13F-HR filings, May 2026 (period ending March 31, 2026)
ASCHENBRENNER_HOLDINGS = {
    "BE": {"name": "Bloom Energy", "theme": "power/fuel_cells", "weight_pct": 16.0},
    "LITE": {"name": "Lumentum Holdings", "theme": "optical_interconnects", "weight_pct": 8.7},
    "CRWV": {"name": "CoreWeave", "theme": "gpu_cloud", "weight_pct": 7.9},
    "SNDK": {"name": "SanDisk", "theme": "memory_storage", "weight_pct": 5.3},
    "IREN": {"name": "IREN Limited", "theme": "bitcoin_miner_power", "weight_pct": 4.5},
    "CORZ": {"name": "Core Scientific", "theme": "bitcoin_miner_power", "weight_pct": 4.2},
    "APLD": {"name": "Applied Digital", "theme": "data_center", "weight_pct": 3.8},
    "INTC": {"name": "Intel", "theme": "semiconductor", "weight_pct": 3.5},
    "CLSK": {"name": "CleanSpark", "theme": "bitcoin_miner_power", "weight_pct": 3.2},
    "RIOT": {"name": "Riot Platforms", "theme": "bitcoin_miner_power", "weight_pct": 2.8},
    "VST": {"name": "Vistra", "theme": "power/utility", "weight_pct": 2.5},
    "CEG": {"name": "Constellation Energy", "theme": "power/nuclear", "weight_pct": 2.3},
}

# Fund launch date — Sept 2024
FUND_LAUNCH = "2024-09-01"


@dataclass
class BacktestResult:
    ticker: str
    name: str
    entry_price: float
    current_price: float
    return_pct: float
    is_aschenbrenner_holding: bool
    aschenbrenner_theme: Optional[str] = None


def backtest_recommendations(
    tickers: List[str],
    entry_date: str = FUND_LAUNCH,
    lookback_days: int = 0,
) -> List[BacktestResult]:
    """Fetch historical prices and compute returns since entry_date."""
    results = []

    for ticker in tickers:
        ticker_upper = ticker.upper()
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=entry_date, auto_adjust=True)

            if hist.empty or len(hist) < 2:
                results.append(BacktestResult(
                    ticker=ticker_upper,
                    name="N/A",
                    entry_price=0.0,
                    current_price=0.0,
                    return_pct=0.0,
                    is_aschenbrenner_holding=ticker_upper in ASCHENBRENNER_HOLDINGS,
                ))
                continue

            entry_price = float(hist["Close"].iloc[0])
            current_price = float(hist["Close"].iloc[-1])
            return_pct = round((current_price / entry_price - 1) * 100, 1)

            info = stock.info
            name = info.get("shortName") or info.get("longName") or ticker_upper

            ab_data = ASCHENBRENNER_HOLDINGS.get(ticker_upper)
            results.append(BacktestResult(
                ticker=ticker_upper,
                name=name,
                entry_price=round(entry_price, 2),
                current_price=round(current_price, 2),
                return_pct=return_pct,
                is_aschenbrenner_holding=ab_data is not None,
                aschenbrenner_theme=ab_data["theme"] if ab_data else None,
            ))
        except Exception as e:
            print(f"[Backtest] Error for {ticker}: {e}")
            results.append(BacktestResult(
                ticker=ticker_upper,
                name="Error",
                entry_price=0.0,
                current_price=0.0,
                return_pct=0.0,
                is_aschenbrenner_holding=ticker_upper in ASCHENBRENNER_HOLDINGS,
            ))

    return results


def print_backtest_report(results: List[BacktestResult]) -> str:
    """Format backtest results as markdown."""
    lines = [
        "### Backtest: Situational Awareness LP (since Sept 2024)",
        "",
        "| Ticker | Name | Entry | Current | Return | Aschenbrenner? |",
        "|--------|------|-------|---------|--------|----------------|",
    ]

    for r in results:
        ab_flag = f"✅ {r.aschenbrenner_theme}" if r.is_aschenbrenner_holding else "❌"
        lines.append(
            f"| {r.ticker} | {r.name[:30]} | ${r.entry_price:,.2f} | "
            f"${r.current_price:,.2f} | {r.return_pct:+.1f}% | {ab_flag} |"
        )

    # Summary stats
    asch_matches = [r for r in results if r.is_aschenbrenner_holding]
    avg_return = sum(r.return_pct for r in results) / max(1, len(results))
    lines.append("")
    lines.append(f"**Match rate:** {len(asch_matches)}/{len(results)} tickers are in Aschenbrenner's actual portfolio")
    lines.append(f"**Avg return:** {avg_return:+.1f}% since fund launch (Sept 2024)")

    return "\n".join(lines)


def validate_against_thesis(recommended_tickers: List[str]) -> dict:
    """Check how well recommendations align with Aschenbrenner's known strategy."""
    recommended_upper = {t.upper() for t in recommended_tickers}
    asch_tickers = set(ASCHENBRENNER_HOLDINGS.keys())

    matches = recommended_upper & asch_tickers
    misses = recommended_upper - asch_tickers
    missing_asch = asch_tickers - recommended_upper

    return {
        "matches": sorted(matches),
        "false_positives": sorted(misses),
        "missed_holdings": sorted(missing_asch),
        "match_rate": len(matches) / max(1, len(recommended_upper)),
    }
