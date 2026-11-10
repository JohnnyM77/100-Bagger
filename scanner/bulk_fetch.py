"""
bulk_fetch.py — 1-year daily price statistics from EODHD.

One EODHD /eod call per ticker (1 API unit each), run on a small thread pool.
Uses raw (unadjusted) ``close`` for the current price and 52-week range,
consistent with what the ASX and marketindex.com.au display. Tickers EODHD
has no / too little history for are excluded — never filled in.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, timedelta

from . import eodhd

logger = logging.getLogger(__name__)

WORKERS = 8
MIN_DAYS_OF_DATA = 50
TRADING_DAYS_1Y = 252
VOLUME_AVG_WINDOW = 30


@dataclass
class PriceStats:
    """Price-derived statistics for a single ticker over the past 1 year (EODHD EOD)."""

    current_price: float
    high_52w: float
    low_52w: float
    pct_above_low: float          # ((current - low) / low) * 100
    pct_below_high: float         # ((high - current) / high) * 100
    volume_avg_30d: float         # 30-day average daily volume
    price_12m_ago: float | None   # close ~252 trading days ago
    return_1y_pct: float | None   # ((current - price_12m_ago) / price_12m_ago) * 100
    last_date: str = ""           # EODHD trading date of current_price


def _compute_stats(rows: list[dict]) -> PriceStats | None:
    """PriceStats from EODHD /eod rows (oldest first). None if data is insufficient."""
    rows = [r for r in rows if eodhd.num(r.get("close")) is not None]
    if len(rows) < MIN_DAYS_OF_DATA:
        return None
    close = [eodhd.num(r["close"]) for r in rows]
    highs = [eodhd.num(r.get("high")) or c for r, c in zip(rows, close)]
    lows = [eodhd.num(r.get("low")) or c for r, c in zip(rows, close)]
    vols = [eodhd.num(r.get("volume")) or 0.0 for r in rows]

    current = close[-1]
    high_52w, low_52w = max(highs), min(lows)
    pct_above_low = (current - low_52w) / low_52w * 100 if low_52w > 0 else 0.0
    pct_below_high = (high_52w - current) / high_52w * 100 if high_52w > 0 else 0.0
    vol_window = vols[-VOLUME_AVG_WINDOW:]

    if len(close) >= TRADING_DAYS_1Y:
        price_12m_ago = close[-TRADING_DAYS_1Y]
    else:
        price_12m_ago = close[0]   # earliest EODHD close in the window
    ret = (current - price_12m_ago) / price_12m_ago * 100 if price_12m_ago > 0 else None

    return PriceStats(
        current_price=current,
        high_52w=high_52w,
        low_52w=low_52w,
        pct_above_low=round(pct_above_low, 2),
        pct_below_high=round(pct_below_high, 2),
        volume_avg_30d=round(sum(vol_window) / len(vol_window), 0) if vol_window else 0.0,
        price_12m_ago=price_12m_ago,
        return_1y_pct=round(ret, 2) if ret is not None else None,
        last_date=str(rows[-1].get("date", "")),
    )


def fetch_price_stats(tickers: list[str]) -> dict[str, PriceStats]:
    """Fetch ~1 year of EODHD daily prices for each ticker (EODHD symbols, e.g. BHP.AU)."""
    start = date.today() - timedelta(days=380)
    results: dict[str, PriceStats] = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = {pool.submit(eodhd.eod, t, start): t for t in tickers}
        for i, fut in enumerate(as_completed(futs), 1):
            t = futs[fut]
            try:
                stats = _compute_stats(fut.result())
                if stats is not None:
                    results[t] = stats
            except eodhd.EODHDError as exc:
                logger.warning("EODHD prices for %s: %s", t, exc)
            if i % 200 == 0:
                print(f"  prices {i}/{len(tickers)}")
    print(f"Price fetch complete: {len(results)}/{len(tickers)} tickers had sufficient EODHD data")
    return results
