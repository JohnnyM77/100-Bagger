"""
screener.py — Apply 100-bagger candidate filters to PriceStats.

Filter categories
-----------------
MOMENTUM   : 1-year return >= 30% AND at least one secondary condition.
BREAKOUT   : Tagged on MOMENTUM candidates with return >= 100%.
DEEP_VALUE : Return -20% to +20%, near 52-week low, adequate volume.

A ticker can only match one category (BREAKOUT takes precedence over MOMENTUM).
"""

import logging
from dataclasses import dataclass

from .bulk_fetch import PriceStats
from .universe import UniverseEntry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds (all percentages are % values, e.g. 30 means 30%)
# ---------------------------------------------------------------------------

# PRIMARY
MOMENTUM_MIN_RETURN_1Y = 30.0

# SECONDARY (at least one required alongside PRIMARY)
NEAR_HIGH_MAX_PCT_BELOW = 20.0
BREAKOUT_MIN_RETURN_1Y = 100.0
MOMENTUM_MIN_VOLUME = 50_000

# DEEP VALUE
DEEP_VALUE_RETURN_MIN = -20.0
DEEP_VALUE_RETURN_MAX = 20.0
DEEP_VALUE_MAX_PCT_ABOVE_LOW = 10.0
DEEP_VALUE_MIN_VOLUME = 100_000


@dataclass
class ScreenResult:
    """Outcome of applying the screener to a single ticker."""

    ticker: str
    company_name: str
    exchange: str
    gics_sector: str
    price_stats: PriceStats
    filter_matched: str   # "MOMENTUM", "BREAKOUT", or "DEEP_VALUE"
    passed: bool


def _check_momentum(stats: PriceStats) -> tuple[bool, str]:
    """
    Return (passed, label) for the MOMENTUM / BREAKOUT filters.

    BREAKOUT is a sub-label of MOMENTUM (return >= 100% automatically
    satisfies the secondary condition and gets the BREAKOUT label).
    """
    ret = stats.return_1y_pct
    if ret is None or ret < MOMENTUM_MIN_RETURN_1Y:
        return False, ""

    # Check secondary conditions
    near_high = stats.pct_below_high <= NEAR_HIGH_MAX_PCT_BELOW
    breakout = ret >= BREAKOUT_MIN_RETURN_1Y
    liquid = stats.volume_avg_30d >= MOMENTUM_MIN_VOLUME

    if not (near_high or breakout or liquid):
        return False, ""

    label = "BREAKOUT" if breakout else "MOMENTUM"
    return True, label


def _check_deep_value(stats: PriceStats) -> tuple[bool, str]:
    """Return (passed, label) for the DEEP_VALUE filter."""
    ret = stats.return_1y_pct
    if ret is None:
        return False, ""

    flat = DEEP_VALUE_RETURN_MIN <= ret <= DEEP_VALUE_RETURN_MAX
    near_low = stats.pct_above_low <= DEEP_VALUE_MAX_PCT_ABOVE_LOW
    liquid = stats.volume_avg_30d >= DEEP_VALUE_MIN_VOLUME

    if flat and near_low and liquid:
        return True, "DEEP_VALUE"
    return False, ""


def screen(
    universe: list[UniverseEntry],
    price_data: dict[str, PriceStats],
) -> list[ScreenResult]:
    """
    Apply all filters to the priced universe and return ScreenResult list.

    Args:
        universe : Full universe entries (used for metadata).
        price_data: Mapping of ticker -> PriceStats from bulk_fetch.

    Returns:
        List of ScreenResult for every ticker that passed at least one filter.
        Tickers missing from price_data are skipped silently.
    """
    # Build a fast lookup from ticker -> UniverseEntry
    meta: dict[str, UniverseEntry] = {e.ticker: e for e in universe}

    passed: list[ScreenResult] = []
    skipped_no_data = 0

    for ticker, stats in price_data.items():
        entry = meta.get(ticker)
        company_name = entry.company_name if entry else ticker
        exchange = entry.exchange if entry else ""
        gics_sector = entry.gics_sector if entry else ""

        matched, label = _check_momentum(stats)
        if not matched:
            matched, label = _check_deep_value(stats)

        if matched:
            passed.append(
                ScreenResult(
                    ticker=ticker,
                    company_name=company_name,
                    exchange=exchange,
                    gics_sector=gics_sector,
                    price_stats=stats,
                    filter_matched=label,
                    passed=True,
                )
            )

    logger.info(
        "Screener: %d/%d tickers passed (%d MOMENTUM, %d BREAKOUT, %d DEEP_VALUE)",
        len(passed),
        len(price_data),
        sum(1 for r in passed if r.filter_matched == "MOMENTUM"),
        sum(1 for r in passed if r.filter_matched == "BREAKOUT"),
        sum(1 for r in passed if r.filter_matched == "DEEP_VALUE"),
    )

    return passed
