"""Theme-to-company mapper.

Takes investment themes extracted from a thesis and maps each to
specific public companies using web search. Anchor mappings provide
fast paths for common themes; web search is the generic fallback.

Design principles for generic use:
- Anchors cover broad sectors, not any one fund's picks.
- Web search is the primary mechanism for novel themes.
- Returned tickers are validated via yfinance before scoring.
"""

from __future__ import annotations

import re
from typing import Dict, List, Set

from .web_search import WebSearchTool


# Anchor mappings: broad sectors → likely pure-play tickers.
# Ordered by descending relevance (best match first).
# These are shortcuts; web search handles everything else.
THEME_ANCHORS: Dict[str, List[str]] = {
    # Energy & power — specific bottlenecks
    "fuel cell": ["BE", "PLUG", "FCEL"],
    "nuclear power": ["CEG", "BWXT", "CCJ"],
    "solar panel": ["ENPH", "FSLR", "SEDG", "RUN"],
    "solar": ["ENPH", "FSLR", "SEDG", "RUN"],
    "battery technology": ["TSLA", "QS", "ENVX", "SLDP"],
    "battery": ["TSLA", "QS", "ENVX", "SLDP"],
    # AI & compute — specific bottlenecks
    "gpu cloud": ["CRWV", "NVDA"],
    "cloud infrastructure": ["CRWV", "EQIX", "DLR"],
    "data center operator": ["APLD", "EQIX", "DLR"],
    "optical interconnect": ["LITE", "COHR", "MRVL"],
    "memory chip": ["SNDK", "MU", "WDC"],
    "memory": ["SNDK", "MU", "WDC"],
    "storage": ["SNDK", "WDC", "PSTG"],
    "semiconductor foundry": ["INTC", "TSM", "GFS"],
    "semiconductor": ["NVDA", "AMD", "INTC", "TSM", "AVGO"],
    "gpu": ["NVDA", "AMD", "INTC"],
    # Crypto — specific
    "bitcoin miner": ["IREN", "CORZ", "CLSK", "RIOT", "MARA"],
    "bitcoin mining": ["IREN", "CORZ", "CLSK", "RIOT", "MARA"],
    # Biotech — specific
    "gene therapy": ["REGN", "VRTX", "GILD", "AMGN"],
    "biotech": ["REGN", "VRTX", "GILD", "AMGN", "BIIB"],
    "pharma": ["JNJ", "PFE", "MRK", "ABBV", "LLY"],
    # Cybersecurity — specific
    "cybersecurity": ["CRWD", "PANW", "FTNT", "ZS", "OKTA"],
    "zero trust": ["ZS", "CRWD", "OKTA", "NET"],
    "firewall": ["PANW", "FTNT", "CHKP"],
    # Space — specific
    "space launch": ["RKLB", "SPCE", "LUNR"],
    "satellite internet": ["ASTS", "RKLB", "VSAT"],
    "satellite": ["ASTS", "RKLB", "Iridium", "VSAT"],
    # Fintech — specific
    "fintech": ["SQ", "PYPL", "SOFI", "AFRM", "HOOD"],
    "digital payment": ["SQ", "PYPL", "AFRM", "SOFI"],
    "payments": ["V", "MA", "SQ", "PYPL", "AFRM"],
    # Commodities — specific
    "lithium mining": ["ALB", "SQM", "LTHM", "PLL"],
    "lithium": ["ALB", "SQM", "LTHM", "PLL"],
    "copper mining": ["FCX", "SCCO", "TECK"],
    "copper": ["FCX", "SCCO", "TECK"],
    "gold mining": ["NEM", "GOLD", "AU"],
    "gold": ["NEM", "GOLD", "AU"],
    "uranium": ["CCJ", "UUUU", "DNN"],
    # EV / auto — specific
    "electric vehicle": ["TSLA", "RIVN", "LCID", "NIO", "XPEV"],
    "ev": ["TSLA", "RIVN", "LCID", "NIO", "XPEV"],
}

# Common false positives when extracting tickers from web text.
FALSE_POSITIVES = {
    "AI", "CEO", "USA", "NYSE", "NASDAQ", "ETF", "IPO", "GDP", "FED", "SEC",
    "EV", "SPAC", "REIT", "EPS", "CEO", "CFO", "CTO", "COO", "LLC", "INC",
    "LTD", "CORP", "PLC", "AG", "SA", "GMBH", "BV", "OY", "AB", "YTD", "QOQ",
    "YOY", "MoM", "AI", "ML", "API", "SaaS", "PaaS", "IaaS", "GPU", "CPU",
    "RAM", "SSD", "HDD", "NAND", "DRAM", "IoT", "AR", "VR", "MR", "XR",
}


class ThemeMapper:
    """Maps abstract investment themes to specific public company tickers."""

    def __init__(self) -> None:
        self.search = WebSearchTool()

    def map_themes(self, themes: List[str], max_results_per_theme: int = 3) -> List[dict]:
        """
        For each theme, search for public companies and return tickers.
        Deduplicates across themes.
        """
        seen_tickers: Set[str] = set()
        mappings = []

        for theme in themes:
            tickers = self._tickers_for_theme(theme, max_results_per_theme)
            for t in tickers:
                t_upper = t.upper()
                if t_upper in seen_tickers:
                    continue
                seen_tickers.add(t_upper)
                mappings.append({
                    "ticker": t_upper,
                    "theme": theme,
                })
        return mappings

    def _tickers_for_theme(self, theme: str, max_results: int) -> List[str]:
        """Search web for companies matching a theme and extract tickers."""
        # 1. Check anchor mappings first
        anchors = self._anchor_tickers(theme, max_results=max_results)

        # 2. Web search for additional companies
        query = self._build_search_query(theme)
        try:
            results = self.search.run(query, max_results=max_results)
        except Exception:
            results = []

        extracted = self._extract_tickers_from_results(results)
        # Validate web search tickers before using them
        extracted = self._validate_tickers(extracted)

        # Merge anchors + extracted, prefer anchors
        combined = anchors + [t for t in extracted if t not in anchors]
        return combined[:max_results]

    @staticmethod
    def _build_search_query(theme: str) -> str:
        """Build a targeted search query for finding tickers by theme."""
        # Strip common filler words
        clean = theme.lower()
        for filler in ["according to", "based on", "thesis on", "investment in", "best"]:
            clean = clean.replace(filler, "")
        clean = clean.strip()
        return f"{clean} public companies stock ticker"

    def _anchor_tickers(self, theme: str, max_results: int = 3) -> List[str]:
        """Return known tickers for a theme keyword, capped at max_results.

        Collects tickers from ALL matching keywords, then deduplicates
        while preserving order (first mention wins).
        """
        theme_lower = theme.lower()
        tickers = []
        for keyword, tickers_list in THEME_ANCHORS.items():
            if keyword in theme_lower:
                tickers.extend(tickers_list)
        # Deduplicate preserving order
        seen = set()
        deduped = []
        for t in tickers:
            if t not in seen:
                seen.add(t)
                deduped.append(t)
        return deduped[:max_results]

    @staticmethod
    def _extract_tickers_from_results(results) -> List[str]:
        """Extract ticker symbols from search result snippets."""
        tickers = []
        # Match tickers in common formats: (TICKER), TICKER stock, $TICKER
        ticker_patterns = [
            re.compile(r'\(([A-Z]{1,5})\)'),  # "Company (TICKER)"
            re.compile(r'\$([A-Z]{1,5})\b'),  # "$TICKER"
            re.compile(r'\b([A-Z]{2,5})\b(?:\s+(?:stock|share|ticker|NYSE|NASDAQ))'),
        ]
        for r in results:
            text = f"{r.title} {r.snippet}"
            found = []
            for pat in ticker_patterns:
                found.extend(pat.findall(text))
            # Fallback: simple uppercase words
            simple = re.findall(r'\b([A-Z]{2,5})\b', text)
            found.extend(simple)
            filtered = [t for t in found if t not in FALSE_POSITIVES and t.isalpha()]
            tickers.extend(filtered)
        return tickers

    @staticmethod
    def _validate_tickers(tickers: List[str]) -> List[str]:
        """Filter out tickers that don't exist on Yahoo Finance.
        
        This is a lightweight check using yfinance info() to avoid
        scoring non-existent or delisted tickers later.
        """
        import yfinance as yf
        valid = []
        for t in tickers:
            try:
                info = yf.Ticker(t).info
                # If we get a name back, ticker exists
                if info.get("shortName") or info.get("longName"):
                    valid.append(t)
            except Exception:
                pass
        return valid
