"""
bulk_fetch.py — Batch price-data fetcher using yf.download().

Fetches 1-year daily OHLCV for large ticker lists in batches of 100,
returning a PriceStats dataclass per ticker.  Uses auto_adjust=False
(raw unadjusted prices, consistent with marketindex.com.au).
"""

import logging
import time
from dataclasses import dataclass

import pandas as pd
import yfinance as yf

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
BATCH_SLEEP_SECONDS = 2
MIN_DAYS_OF_DATA = 50
TRADING_DAYS_1Y = 252
VOLUME_AVG_WINDOW = 30


@dataclass
class PriceStats:
    """Price-derived statistics for a single ticker over the past 1 year."""

    current_price: float
    high_52w: float
    low_52w: float
    pct_above_low: float          # ((current - low) / low) * 100
    pct_below_high: float         # ((high - current) / high) * 100
    volume_avg_30d: float         # 30-day average daily volume
    price_12m_ago: float | None   # close ~252 trading days ago
    return_1y_pct: float | None   # ((current - price_12m_ago) / price_12m_ago) * 100


def _download_batch(tickers: list[str]) -> pd.DataFrame:
    """
    Download 1 year of daily OHLCV for a list of tickers.

    Returns a MultiIndex DataFrame (field, ticker) or empty DataFrame on error.
    """
    try:
        data = yf.download(
            tickers,
            period="1y",
            interval="1d",
            auto_adjust=False,
            progress=False,
            threads=True,
        )
        return data
    except Exception as exc:
        logger.warning("yf.download batch failed: %s", exc)
        return pd.DataFrame()


def _extract_series(data: pd.DataFrame, field: str, ticker: str) -> pd.Series:
    """
    Safely extract a single-ticker series from a (possibly MultiIndex) DataFrame.

    yf.download() with a list of tickers returns a MultiIndex; with a single
    ticker string it returns a flat DataFrame.  We always pass lists so we
    expect MultiIndex, but guard against the flat case.
    """
    if data.empty:
        return pd.Series(dtype=float)

    try:
        if isinstance(data.columns, pd.MultiIndex):
            if (field, ticker) in data.columns:
                return data[(field, ticker)].dropna()
        else:
            # Single-ticker flat DataFrame
            if field in data.columns:
                return data[field].dropna()
    except Exception:
        pass
    return pd.Series(dtype=float)


def _compute_stats(
    ticker: str,
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    volume: pd.Series,
) -> PriceStats | None:
    """
    Compute PriceStats from per-field Series.  Returns None if data is insufficient.
    """
    if len(close) < MIN_DAYS_OF_DATA:
        return None

    current_price = float(close.iloc[-1])
    high_52w = float(high.max())
    low_52w = float(low.min())

    pct_above_low = ((current_price - low_52w) / low_52w * 100) if low_52w > 0 else 0.0
    pct_below_high = ((high_52w - current_price) / high_52w * 100) if high_52w > 0 else 0.0

    vol_window = volume.iloc[-VOLUME_AVG_WINDOW:]
    volume_avg_30d = float(vol_window.mean()) if len(vol_window) > 0 else 0.0

    price_12m_ago: float | None = None
    return_1y_pct: float | None = None
    if len(close) >= TRADING_DAYS_1Y:
        price_12m_ago = float(close.iloc[-TRADING_DAYS_1Y])
    elif len(close) >= 2:
        price_12m_ago = float(close.iloc[0])   # best available

    if price_12m_ago is not None and price_12m_ago > 0:
        return_1y_pct = (current_price - price_12m_ago) / price_12m_ago * 100

    return PriceStats(
        current_price=current_price,
        high_52w=high_52w,
        low_52w=low_52w,
        pct_above_low=round(pct_above_low, 2),
        pct_below_high=round(pct_below_high, 2),
        volume_avg_30d=round(volume_avg_30d, 0),
        price_12m_ago=price_12m_ago,
        return_1y_pct=round(return_1y_pct, 2) if return_1y_pct is not None else None,
    )


def fetch_price_stats(tickers: list[str]) -> dict[str, PriceStats]:
    """
    Fetch 1-year daily prices for all tickers in batched yf.download() calls.

    Args:
        tickers: List of yfinance-format ticker symbols.

    Returns:
        Dict mapping ticker -> PriceStats.  Tickers with insufficient data
        are silently excluded.
    """
    results: dict[str, PriceStats] = {}
    batches = [tickers[i: i + BATCH_SIZE] for i in range(0, len(tickers), BATCH_SIZE)]
    total_batches = len(batches)

    for batch_num, batch in enumerate(batches, start=1):
        print(
            f"Batch {batch_num}/{total_batches} — "
            f"fetching {len(batch)} tickers "
            f"({(batch_num - 1) * BATCH_SIZE}/{len(tickers)} done)"
        )

        data = _download_batch(batch)

        for ticker in batch:
            try:
                close = _extract_series(data, "Close", ticker)
                high = _extract_series(data, "High", ticker)
                low = _extract_series(data, "Low", ticker)
                volume = _extract_series(data, "Volume", ticker)

                stats = _compute_stats(ticker, close, high, low, volume)
                if stats is not None:
                    results[ticker] = stats
            except Exception as exc:
                logger.warning("Error processing %s: %s", ticker, exc)

        if batch_num < total_batches:
            time.sleep(BATCH_SLEEP_SECONDS)

    print(
        f"Price fetch complete: {len(results)}/{len(tickers)} tickers "
        f"had sufficient data"
    )
    return results
