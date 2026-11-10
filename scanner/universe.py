"""
universe.py — Fetch and cache the ticker universe from EODHD.

ASX source : EODHD /exchange-symbol-list/AU (Common Stock only)
SGX        : not on the EODHD plan — skipped with a warning, never borrowed
             from another source (see CLAUDE.md).
Cache      : scanner/data/universe_cache_eodhd.json, 24-hour TTL
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

from . import eodhd

logger = logging.getLogger(__name__)

CACHE_PATH = Path(__file__).parent / "data" / "universe_cache_eodhd.json"
CACHE_TTL_HOURS = 24


@dataclass
class UniverseEntry:
    """Single ticker entry in the universe."""

    exchange: str
    ticker: str          # EODHD format, e.g. "BHP.AU"
    company_name: str
    gics_sector: str


def fetch_asx() -> list[UniverseEntry]:
    """Every ASX common stock EODHD lists."""
    try:
        rows = eodhd.exchange_symbols("AU")
    except eodhd.EODHDError as exc:
        logger.error("EODHD symbol list failed: %s", exc)
        return []
    entries = [
        UniverseEntry(exchange="ASX", ticker=f"{r['Code']}.AU",
                      company_name=str(r.get("Name") or "").strip(), gics_sector="")
        for r in rows
        if r.get("Type") == "Common Stock" and str(r.get("Code") or "").isalnum()
    ]
    logger.info("ASX universe (EODHD): %d common stocks", len(entries))
    return entries


def fetch_sgx() -> list[UniverseEntry]:
    """SGX is not on the EODHD plan, so there is no SGX universe."""
    logger.warning("SGX skipped: not covered by the EODHD plan (no other source is used)")
    return []


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _load_cache() -> list[UniverseEntry] | None:
    """Return cached entries if the cache file exists and is within TTL."""
    if not CACHE_PATH.exists():
        return None
    try:
        payload = json.loads(CACHE_PATH.read_text())
        cached_at = datetime.fromisoformat(payload["timestamp"])
        if datetime.now() - cached_at > timedelta(hours=CACHE_TTL_HOURS):
            logger.info("Universe cache expired (%.1f h old)", (datetime.now() - cached_at).total_seconds() / 3600)
            return None
        entries = [UniverseEntry(**d) for d in payload["data"]]
        logger.info("Loaded %d tickers from cache (age %.1f h)", len(entries), (datetime.now() - cached_at).total_seconds() / 3600)
        return entries
    except Exception as exc:
        logger.warning("Cache read failed (%s) — will re-fetch", exc)
        return None


def _save_cache(entries: list[UniverseEntry]) -> None:
    """Persist entries to the cache file."""
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "timestamp": datetime.now().isoformat(),
        "data": [asdict(e) for e in entries],
    }
    CACHE_PATH.write_text(json.dumps(payload, indent=2))
    logger.info("Universe cache saved (%d entries)", len(entries))


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_universe(
    exchanges: list[str] | None = None,
    force_refresh: bool = False,
) -> list[UniverseEntry]:
    """
    Return the combined ticker universe for the requested exchanges.

    Args:
        exchanges: ["ASX"], ["SGX"], or None / ["ASX", "SGX"] for both.
        force_refresh: Bypass the cache and re-fetch.

    Returns:
        List of UniverseEntry, one per ticker.
    """
    if exchanges is None:
        exchanges = ["ASX"]

    exchanges = [e.upper() for e in exchanges]

    if not force_refresh:
        cached = _load_cache()
        if cached is not None:
            # Filter to requested exchanges
            return [e for e in cached if e.exchange in exchanges]

    all_entries: list[UniverseEntry] = []
    if "ASX" in exchanges:
        all_entries.extend(fetch_asx())
    if "SGX" in exchanges:
        all_entries.extend(fetch_sgx())

    if all_entries:
        _save_cache(all_entries)

    return [e for e in all_entries if e.exchange in exchanges]
