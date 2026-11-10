"""
enricher.py — Fetch fundamental data and score filtered candidates.

Uses EODHD /fundamentals (cached 7 days, see scanner/eodhd.py) for the
small candidate set (typically 50-200 stocks).  Every field is None if
EODHD does not have it — never estimated.

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
from dataclasses import dataclass

from . import eodhd
from .screener import ScreenResult

logger = logging.getLogger(__name__)

@dataclass
class FundamentalSnapshot:
    """Fundamental fields from the EODHD fundamentals record."""

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


def _pos(v: object) -> float | None:
    """EODHD reports a missing PE as 0; treat <= 0 as not available."""
    f = eodhd.num(v)
    return f if f is not None and f > 0 else None


def _latest_yearly(f: dict, statement: str) -> dict:
    rows = (((f.get("Financials") or {}).get(statement) or {}).get("yearly")) or {}
    if not rows:
        return {}
    return rows[max(rows)] or {}


def snapshot_from_eodhd(f: dict) -> FundamentalSnapshot:
    hi = f.get("Highlights") or {}
    val = f.get("Valuation") or {}
    bs = _latest_yearly(f, "Balance_Sheet")
    cf = _latest_yearly(f, "Cash_Flow")
    debt = eodhd.num(bs.get("shortLongTermDebtTotal"))
    equity = eodhd.num(bs.get("totalStockholderEquity"))
    cash = eodhd.num(bs.get("cashAndShortTermInvestments"))
    if cash is None:
        cash = eodhd.num(bs.get("cash"))
    return FundamentalSnapshot(
        market_cap=eodhd.num(hi.get("MarketCapitalization")),
        trailing_pe=_pos(val.get("TrailingPE")),
        forward_pe=_pos(val.get("ForwardPE")),
        price_to_book=_pos(val.get("PriceBookMRQ")),
        price_to_sales=_pos(val.get("PriceSalesTTM")),
        revenue_growth=eodhd.num(hi.get("QuarterlyRevenueGrowthYOY")),
        earnings_growth=eodhd.num(hi.get("QuarterlyEarningsGrowthYOY")),
        return_on_equity=eodhd.num(hi.get("ReturnOnEquityTTM")),
        debt_to_equity=(debt / equity) if debt is not None and equity and equity > 0 else None,
        free_cashflow=eodhd.num(cf.get("freeCashFlow")),
        total_cash=cash,
        total_debt=debt,
    )


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
            snap = snapshot_from_eodhd(eodhd.fundamentals(ticker))
            snap.score = _score(snap, candidate.price_stats.return_1y_pct)
            results[ticker] = snap
        except eodhd.EODHDError as exc:
            logger.warning("EODHD fundamentals failed for %s: %s", ticker, exc)

    print()   # newline after the \r progress line
    logger.info("Enrichment complete: %d/%d tickers", len(results), total)
    return results
