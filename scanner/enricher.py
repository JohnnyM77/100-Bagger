"""
enricher.py — Fetch fundamental data and score filtered candidates.

Uses yf.Ticker().info (one at a time) for the small candidate set
(typically 50-200 stocks).  Every field degrades gracefully to None
if the data is unavailable.

Scoring (0-10, 1 point per condition met):
  1.  trailing_pe < 30
  2.  forward_pe < trailing_pe
  3.  price_to_book < 5
  4.  revenue_growth > 15%
  5.  earnings_growth > 20%
  6.  return_on_equity > 15%
  7.  debt_to_equity < 1.0
  8.  free_cashflow > 0
  9.  market_cap < $2B
  10. 1-year price return > 50%
"""

import logging
import time
from dataclasses import dataclass

import yfinance as yf

from .screener import ScreenResult

logger = logging.getLogger(__name__)

SLEEP_BETWEEN_CALLS = 0.5   # seconds


@dataclass
class FundamentalSnapshot:
    """Raw fundamental fields pulled from yf.Ticker().info."""

    market_cap: float | None
    trailing_pe: float | None
    forward_pe: float | None
    price_to_book: float | None
    price_to_sales: float | None
    revenue_growth: float | None      # yoy, decimal (0.20 = 20%)
    earnings_growth: float | None     # yoy, decimal
    return_on_equity: float | None    # decimal
    debt_to_equity: float | None
    free_cashflow: float | None
    total_cash: float | None
    total_debt: float | None
    score: int = 0                    # 0-10


def _safe_float(info: dict, key: str) -> float | None:
    """Extract a float from yf info dict, returning None on missing / non-numeric."""
    val = info.get(key)
    if val is None:
        return None
    try:
        f = float(val)
        return f if f == f else None   # filter NaN
    except (TypeError, ValueError):
        return None


def _score(snap: FundamentalSnapshot, return_1y_pct: float | None) -> int:
    """Compute 0-10 score: 1 point per condition met."""
    points = 0

    pe = snap.trailing_pe
    fpe = snap.forward_pe

    if pe is not None and 0 < pe < 30:
        points += 1
    if pe is not None and fpe is not None and 0 < fpe < pe:
        points += 1
    if snap.price_to_book is not None and 0 < snap.price_to_book < 5:
        points += 1
    if snap.revenue_growth is not None and snap.revenue_growth > 0.15:
        points += 1
    if snap.earnings_growth is not None and snap.earnings_growth > 0.20:
        points += 1
    if snap.return_on_equity is not None and snap.return_on_equity > 0.15:
        points += 1
    if snap.debt_to_equity is not None and snap.debt_to_equity < 1.0:
        points += 1
    if snap.free_cashflow is not None and snap.free_cashflow > 0:
        points += 1
    if snap.market_cap is not None and snap.market_cap < 2_000_000_000:
        points += 1
    if return_1y_pct is not None and return_1y_pct > 50:
        points += 1

    return points


def enrich(candidates: list[ScreenResult]) -> dict[str, FundamentalSnapshot]:
    """
    Fetch fundamental data for each candidate and return a scored snapshot.

    Args:
        candidates: List of ScreenResult from the screener step.

    Returns:
        Dict mapping ticker -> FundamentalSnapshot (with .score populated).
        Tickers that error are logged and excluded from the result.
    """
    results: dict[str, FundamentalSnapshot] = {}
    total = len(candidates)

    for idx, candidate in enumerate(candidates, start=1):
        ticker = candidate.ticker
        print(f"  Enriching {ticker} ({idx}/{total})...", end="\r")

        try:
            info = yf.Ticker(ticker).info or {}

            snap = FundamentalSnapshot(
                market_cap=_safe_float(info, "marketCap"),
                trailing_pe=_safe_float(info, "trailingPE"),
                forward_pe=_safe_float(info, "forwardPE"),
                price_to_book=_safe_float(info, "priceToBook"),
                price_to_sales=_safe_float(info, "priceToSalesTrailing12Months"),
                revenue_growth=_safe_float(info, "revenueGrowth"),
                earnings_growth=_safe_float(info, "earningsGrowth"),
                return_on_equity=_safe_float(info, "returnOnEquity"),
                debt_to_equity=_safe_float(info, "debtToEquity"),
                free_cashflow=_safe_float(info, "freeCashflow"),
                total_cash=_safe_float(info, "totalCash"),
                total_debt=_safe_float(info, "totalDebt"),
            )
            snap.score = _score(snap, candidate.price_stats.return_1y_pct)
            results[ticker] = snap

        except Exception as exc:
            logger.warning("Enrichment failed for %s: %s", ticker, exc)

        time.sleep(SLEEP_BETWEEN_CALLS)

    print()   # newline after the \r progress line
    logger.info("Enrichment complete: %d/%d tickers", len(results), total)
    return results
