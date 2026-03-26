"""
report_builder.py — Build JSON and Markdown scan reports.

Outputs
-------
  scanner/data/outputs/YYYY-MM-DD_scan_results.json  — full machine-readable
  scanner/data/outputs/YYYY-MM-DD_scan_results.md    — human-readable summary
"""

import json
import logging
from dataclasses import asdict
from datetime import date
from pathlib import Path

from .enricher import FundamentalSnapshot
from .screener import ScreenResult

logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "data" / "outputs"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_pct(val: float | None, decimals: int = 1) -> str:
    """Format a percentage value, or return '—' if None."""
    if val is None:
        return "—"
    return f"{val:+.{decimals}f}%"


def _fmt_float(val: float | None, decimals: int = 2) -> str:
    """Format a float, or return '—' if None."""
    if val is None:
        return "—"
    return f"{val:.{decimals}f}"


def _fmt_mcap(val: float | None) -> str:
    """Format market cap in human-readable form (B / M)."""
    if val is None:
        return "—"
    if val >= 1e9:
        return f"${val / 1e9:.2f}B"
    return f"${val / 1e6:.0f}M"


def _candidate_to_dict(
    result: ScreenResult,
    fundamentals: dict[str, FundamentalSnapshot],
) -> dict:
    """Serialise a ScreenResult + FundamentalSnapshot to a plain dict."""
    fund = fundamentals.get(result.ticker)
    d = {
        "ticker": result.ticker,
        "company_name": result.company_name,
        "exchange": result.exchange,
        "gics_sector": result.gics_sector,
        "filter_matched": result.filter_matched,
        "score": fund.score if fund else None,
        "price_stats": asdict(result.price_stats),
        "fundamentals": asdict(fund) if fund else None,
    }
    return d


# ---------------------------------------------------------------------------
# Markdown helpers
# ---------------------------------------------------------------------------

def _md_row(result: ScreenResult, fund: FundamentalSnapshot | None) -> str:
    """One markdown table row for a candidate."""
    score = f"{fund.score}/10" if fund else "—"
    mcap = _fmt_mcap(fund.market_cap) if fund else "—"
    pe = _fmt_float(fund.trailing_pe, 1) if fund else "—"
    roe = _fmt_pct(fund.return_on_equity * 100 if fund and fund.return_on_equity is not None else None)
    ret = _fmt_pct(result.price_stats.return_1y_pct)

    return (
        f"| {result.ticker} "
        f"| {result.company_name[:35]} "
        f"| {result.gics_sector[:20]} "
        f"| {ret} "
        f"| {score} "
        f"| {mcap} "
        f"| {pe} "
        f"| {roe} |"
    )


def _md_table_header() -> str:
    return (
        "| Ticker | Company | Sector | 1yr Return | Score | Mkt Cap | P/E | ROE |\n"
        "|--------|---------|--------|-----------|-------|---------|-----|-----|"
    )


def _build_markdown(
    results: list[ScreenResult],
    fundamentals: dict[str, FundamentalSnapshot],
    metadata: dict,
) -> str:
    """Construct the full markdown report string."""
    run_date = metadata["date"]
    total_scanned = metadata["total_scanned"]
    candidates_found = metadata["candidates_found"]
    runtime_s = metadata["runtime_seconds"]

    lines: list[str] = [
        f"# 100-Bagger Scan — {run_date}",
        "",
        "## Run Summary",
        f"- **Date:** {run_date}",
        f"- **Tickers scanned:** {total_scanned:,}",
        f"- **Candidates found:** {candidates_found}",
        f"- **Runtime:** {runtime_s:.0f}s",
        "",
    ]

    # Top 10 by score
    enriched = [r for r in results if r.ticker in fundamentals]
    top10 = sorted(enriched, key=lambda r: fundamentals[r.ticker].score, reverse=True)[:10]

    if top10:
        lines += [
            "## Top 10 by Score",
            "",
            _md_table_header(),
        ]
        for r in top10:
            lines.append(_md_row(r, fundamentals.get(r.ticker)))
        lines.append("")

    # Section per filter type
    for label in ["BREAKOUT", "MOMENTUM", "DEEP_VALUE"]:
        group = [r for r in results if r.filter_matched == label]
        if not group:
            continue
        group_sorted = sorted(
            group,
            key=lambda r: (fundamentals[r.ticker].score if r.ticker in fundamentals else -1),
            reverse=True,
        )
        lines += [
            f"## {label} ({len(group)} candidates)",
            "",
            _md_table_header(),
        ]
        for r in group_sorted:
            lines.append(_md_row(r, fundamentals.get(r.ticker)))
        lines.append("")

    lines += [
        "---",
        "*This is a quantitative screen only. Not financial advice.*",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_report(
    results: list[ScreenResult],
    fundamentals: dict[str, FundamentalSnapshot],
    metadata: dict,
) -> tuple[Path, Path]:
    """
    Write JSON and Markdown reports to scanner/data/outputs/.

    Args:
        results     : All ScreenResult objects that passed the screener.
        fundamentals: Mapping of ticker -> FundamentalSnapshot from enricher.
        metadata    : Dict with keys: date, total_scanned, candidates_found,
                      runtime_seconds.

    Returns:
        Tuple of (json_path, md_path).
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    run_date = metadata.get("date", date.today().isoformat())
    stem = f"{run_date}_scan_results"

    # JSON
    json_payload = {
        "metadata": metadata,
        "candidates": [_candidate_to_dict(r, fundamentals) for r in results],
    }
    json_path = OUTPUT_DIR / f"{stem}.json"
    json_path.write_text(json.dumps(json_payload, indent=2))
    logger.info("JSON report saved: %s", json_path)

    # Markdown
    md_content = _build_markdown(results, fundamentals, metadata)
    md_path = OUTPUT_DIR / f"{stem}.md"
    md_path.write_text(md_content)
    logger.info("Markdown report saved: %s", md_path)

    return json_path, md_path
