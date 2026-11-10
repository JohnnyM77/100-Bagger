"""
eodhd.py — the ONE source of market data for this repo.

Every share price, market cap, FX rate and company fundamental the scanner
uses comes from the paid EODHD subscription through this module (the same
account and the same ``EODHD_API_TOKEN`` secret that Bob the Bot uses in
JohnnyM77/Reporting-Agent, whose ``shared/eodhd.py`` this is modelled on).

Rules this module keeps (see CLAUDE.md):

* No fallback, no placeholder. If EODHD has no figure, callers get ``None``
  or an ``EODHDError`` and must show "n/a" with the reason. A missing number
  is acceptable; a guessed one is not.
* Nothing else in the scanner may call yfinance / Yahoo, FMP or any other
  price or fundamentals source (tests/test_eodhd_only.py enforces it).
* Every figure can say where it came from: ``SOURCE`` is the label reports
  print, and EOD rows carry their trading date.

Symbols: EODHD uses CODE.EXCHANGE. ASX is ``.AU`` (not Yahoo's ``.AX``).
Singapore (SGX) is not on the EODHD plan: it raises ``EODHDNotCovered``
rather than borrowing another source.

Plumbing only: stdlib HTTP (urllib), no third-party deps.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Mapping, Optional

logger = logging.getLogger(__name__)

BASE_URL = "https://eodhd.com/api"
SOURCE = "EODHD"
TOKEN_ENV = ("EODHD_API_TOKEN", "EODHD_API_KEY")

CACHE_DIR = Path(__file__).parent / "data" / "cache"
FUNDAMENTALS_TTL_DAYS = 7

# Yahoo-style suffix -> EODHD exchange code. Anything else is not covered.
_EXCHANGE_CODE = {"AX": "AU", "AU": "AU", "ASX": "AU"}
_NOT_COVERED = {"SI": "SGX", "SGX": "SGX"}


class EODHDError(RuntimeError):
    """EODHD could not supply the figure. The message is safe to show."""


class EODHDNotConfigured(EODHDError):
    """No API token in the environment."""


class EODHDNotCovered(EODHDError):
    """The security's exchange is not on the EODHD plan (e.g. SGX)."""


# ---------------------------------------------------------------------------
# Token / symbols
# ---------------------------------------------------------------------------

def get_token(env: Optional[Mapping[str, str]] = None) -> str:
    e = os.environ if env is None else env
    for name in TOKEN_ENV:
        v = (e.get(name) or "").strip()
        if v:
            return v
    return ""


def is_configured() -> bool:
    return bool(get_token())


def symbol(raw: object) -> str:
    """``KPG`` / ``KPG.AX`` / ``ASX:KPG`` / ``KPG.AU`` -> ``KPG.AU``.

    Bare codes are treated as ASX. Raises EODHDNotCovered for SGX.
    """
    text = str(raw or "").strip().upper()
    if not text:
        raise EODHDError("empty ticker")
    if text.endswith(".FOREX"):
        return text
    if ":" in text:
        exch, code = text.split(":", 1)
        text = f"{code}.{exch}"
    if "." in text:
        code, suffix = text.rsplit(".", 1)
    else:
        code, suffix = text, "AU"
    if suffix in _NOT_COVERED:
        raise EODHDNotCovered(f"{text}: {_NOT_COVERED[suffix]} is not on the EODHD plan")
    exch = _EXCHANGE_CODE.get(suffix)
    if not exch:
        raise EODHDNotCovered(f"{text}: exchange '{suffix}' is not supported by this scanner")
    return f"{code}.{exch}"


def display_ticker(sym: str) -> str:
    """``KPG.AU`` -> ``ASX:KPG`` for reports."""
    code, _, exch = sym.partition(".")
    return f"ASX:{code}" if exch == "AU" else sym


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------

_CACHE: dict[str, Any] = {}
stats = {"requests": 0, "cache_hits": 0, "disk_hits": 0}


def _redact(text: str, token: str) -> str:
    return text.replace(token, "***") if token else text


def _get(path: str, params: Optional[dict] = None, *, retries: int = 3, timeout: float = 45.0) -> Any:
    token = get_token()
    if not token:
        raise EODHDNotConfigured("EODHD_API_TOKEN is not set; no market data fetched")
    q = {k: v for k, v in (params or {}).items() if v is not None}
    q["api_token"] = token
    q.setdefault("fmt", "json")
    url = f"{BASE_URL}{path}?{urllib.parse.urlencode(q)}"
    key = f"{path}?{urllib.parse.urlencode(sorted((k, str(v)) for k, v in q.items() if k != 'api_token'))}"
    if key in _CACHE:
        stats["cache_hits"] += 1
        return _CACHE[key]

    last = ""
    for attempt in range(retries + 1):
        try:
            stats["requests"] += 1
            req = urllib.request.Request(url, headers={"User-Agent": "100-Bagger/eodhd"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read().decode("utf-8")
            data = json.loads(body) if body.strip() else None
            if isinstance(data, dict) and data.get("error") and len(data) <= 3:
                raise EODHDError(f"EODHD {path}: {data.get('error')}")
            _CACHE[key] = data
            return data
        except urllib.error.HTTPError as exc:
            status = exc.code
            if status == 404:
                raise EODHDError(f"EODHD {path}: not found (404)") from None
            if status in (402, 403):
                hint = "API limit used up" if status == 402 else "token rejected"
                raise EODHDError(f"EODHD {path}: HTTP {status} ({hint})") from None
            last = f"HTTP {status}"
            if status != 429 and status < 500:
                raise EODHDError(f"EODHD {path}: {last}") from None
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = _redact(f"{type(exc).__name__}: {exc}", token)
        except json.JSONDecodeError:
            raise EODHDError(f"EODHD {path}: response was not JSON") from None
        if attempt < retries:
            time.sleep(2 ** attempt)
    raise EODHDError(f"EODHD {path}: {last} after {retries + 1} attempts")


def _iso(d: object) -> Optional[str]:
    if d is None:
        return None
    if isinstance(d, (dt.date, dt.datetime)):
        return d.strftime("%Y-%m-%d")
    return str(d)[:10]


def num(v: object) -> Optional[float]:
    """EODHD fields arrive as numbers, numeric strings, 'NA' or null."""
    if v is None or isinstance(v, bool):
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f == f and f not in (float("inf"), float("-inf")) else None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def exchange_symbols(exchange: str = "AU") -> list[dict]:
    """/exchange-symbol-list/{EXCHANGE}: [{Code, Name, Country, Exchange, Currency, Type, Isin}]."""
    rows = _get(f"/exchange-symbol-list/{exchange}")
    return rows if isinstance(rows, list) else []


def eod(sym: str, start: object = None, end: object = None) -> list[dict]:
    """/eod/{SYMBOL}: [{date, open, high, low, close, adjusted_close, volume}], oldest first."""
    rows = _get(f"/eod/{sym}", {"from": _iso(start), "to": _iso(end), "period": "d", "order": "a"})
    return rows if isinstance(rows, list) else []


def real_time(sym: str) -> dict:
    """/real-time/{SYMBOL}: delayed live quote; ``close`` is the latest price."""
    data = _get(f"/real-time/{sym}")
    return data if isinstance(data, dict) else {}


def fx_rate(from_ccy: str, to_ccy: str) -> tuple[float, str]:
    """Latest FX rate from EODHD (e.g. AUD->USD). Returns (rate, as-of label)."""
    sym = f"{from_ccy.upper()}{to_ccy.upper()}.FOREX"
    q = real_time(sym)
    rate = num(q.get("close"))
    if rate is None or rate <= 0:
        raise EODHDError(f"EODHD {sym}: no FX rate returned")
    ts = q.get("timestamp")
    asof = dt.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d") if isinstance(ts, (int, float)) else "latest"
    return rate, asof


def screener(filters: list, *, sort: str = "market_capitalization.desc",
             limit: int = 100, offset: int = 0) -> list[dict]:
    """/screener: one page (max 100 rows, 5 API calls). Offset is capped at 999 by EODHD."""
    data = _get("/screener", {
        "filters": json.dumps(filters),
        "sort": sort,
        "limit": limit,
        "offset": offset,
    })
    if isinstance(data, dict):
        rows = data.get("data")
        return rows if isinstance(rows, list) else []
    return data if isinstance(data, list) else []


def fundamentals(sym: str, *, use_disk_cache: bool = True,
                 ttl_days: int = FUNDAMENTALS_TTL_DAYS) -> dict:
    """/fundamentals/{SYMBOL}: the full company record (10 API calls).

    Cached on disk for ``ttl_days`` — fundamentals only change when a
    company reports, and a full ASX hunt would otherwise spend ~10k calls.
    The cache file records when it was fetched so reports can say so.
    """
    path = CACHE_DIR / "fundamentals" / f"{sym}.json"
    if use_disk_cache and path.exists():
        try:
            payload = json.loads(path.read_text())
            fetched = dt.datetime.fromisoformat(payload["fetched_at"])
            if dt.datetime.now() - fetched < dt.timedelta(days=ttl_days):
                stats["disk_hits"] += 1
                return payload["data"]
        except Exception:  # corrupt cache -> refetch
            pass

    data = _get(f"/fundamentals/{sym}")
    if not isinstance(data, dict) or not data:
        raise EODHDError(f"EODHD /fundamentals/{sym}: empty record")
    if use_disk_cache:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"fetched_at": dt.datetime.now().isoformat(), "data": data}))
    return data
