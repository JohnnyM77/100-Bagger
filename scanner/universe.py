"""
universe.py — Fetch and cache the full ticker universe for ASX and SGX.

ASX source : official ASX CSV (free, no auth, updated nightly)
SGX source : stockanalysis.com scrape with graceful fallback
Cache      : scanner/data/universe_cache.json, 24-hour TTL
"""

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

ASX_CSV_URL = "https://www.asx.com.au/asx/research/ASXListedCompanies.csv"
SGX_URL = "https://stockanalysis.com/list/singapore-exchange/"
CACHE_PATH = Path(__file__).parent / "data" / "universe_cache.json"
CACHE_TTL_HOURS = 24

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


@dataclass
class UniverseEntry:
    """Single ticker entry in the universe."""

    exchange: str
    ticker: str          # yfinance format, e.g. "BHP.AX" or "D05.SI"
    company_name: str
    gics_sector: str


# ---------------------------------------------------------------------------
# ASX
# ---------------------------------------------------------------------------

def fetch_asx() -> list[UniverseEntry]:
    """
    Download the official ASX listed-companies CSV and return UniverseEntry list.

    Row 0 of the CSV is a timestamp line ("ASX listed companies as at ...").
    skiprows=1 discards it so the real column headers become the first row.
    """
    logger.info("Fetching ASX universe from %s", ASX_CSV_URL)
    try:
        resp = requests.get(ASX_CSV_URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        from io import StringIO
        df = pd.read_csv(StringIO(resp.text), skiprows=1)
    except Exception as exc:
        logger.error("Failed to fetch ASX CSV: %s", exc)
        return []

    # Normalise column names (strip whitespace)
    df.columns = [c.strip() for c in df.columns]

    required = {"Company name", "ASX code", "GICS industry group"}
    if not required.issubset(df.columns):
        logger.error("Unexpected ASX CSV columns: %s", list(df.columns))
        return []

    entries: list[UniverseEntry] = []
    for _, row in df.iterrows():
        code = str(row["ASX code"]).strip()
        # Keep only pure-alphabetic codes (warrants/options contain digits)
        if not code or not code.isalpha():
            continue
        entries.append(
            UniverseEntry(
                exchange="ASX",
                ticker=f"{code}.AX",
                company_name=str(row["Company name"]).strip(),
                gics_sector=str(row["GICS industry group"]).strip(),
            )
        )

    logger.info("ASX universe: %d tickers", len(entries))
    return entries


# ---------------------------------------------------------------------------
# SGX
# ---------------------------------------------------------------------------

def fetch_sgx() -> list[UniverseEntry]:
    """
    Scrape stockanalysis.com for SGX-listed tickers.

    Returns an empty list (with a warning) if the scrape fails — the page
    may use JS rendering which simple requests cannot access.
    """
    logger.info("Scraping SGX universe from %s", SGX_URL)
    try:
        resp = requests.get(SGX_URL, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        # stockanalysis.com renders a <table> with Symbol and Company Name columns
        table = soup.find("table")
        if table is None:
            raise ValueError("No <table> found on page — site may require JS rendering")

        headers_row = [th.get_text(strip=True) for th in table.find_all("th")]
        try:
            sym_idx = next(
                i for i, h in enumerate(headers_row)
                if re.search(r"symbol|ticker", h, re.I)
            )
            name_idx = next(
                i for i, h in enumerate(headers_row)
                if re.search(r"company|name", h, re.I)
            )
        except StopIteration:
            raise ValueError(f"Could not locate Symbol/Name columns in headers: {headers_row}")

        entries: list[UniverseEntry] = []
        for tr in table.find_all("tr")[1:]:  # skip header row
            cells = tr.find_all("td")
            if len(cells) <= max(sym_idx, name_idx):
                continue
            symbol = cells[sym_idx].get_text(strip=True)
            company = cells[name_idx].get_text(strip=True)
            if not symbol:
                continue
            entries.append(
                UniverseEntry(
                    exchange="SGX",
                    ticker=f"{symbol}.SI",
                    company_name=company,
                    gics_sector="",   # not available from this source
                )
            )

        logger.info("SGX universe: %d tickers", len(entries))
        return entries

    except Exception as exc:
        logger.warning("SGX scrape failed (%s) — returning empty list", exc)
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
        exchanges = ["ASX", "SGX"]

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
