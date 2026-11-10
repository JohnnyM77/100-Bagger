"""
hunt.py — 100-bagger search engine for the ASX, driven by the 100x checklist.

Usage:
    python -m scanner.hunt                    # full ASX hunt, top 30 report + email
    python -m scanner.hunt --limit 40         # only the first 40 pre-filtered names (testing)
    python -m scanner.hunt --ticker KPG       # one company's checklist card
    python -m scanner.hunt --ticker KPG --ticker PME

Pipeline (all data from EODHD — see CLAUDE.md):
  1. EODHD /screener: every ASX stock with market cap, sector, liquidity, EPS
     (a handful of calls, 5 API units each).
  2. Pre-filter on size, liquidity, positive EPS and excluded sectors
     (config/checklist.yaml -> hunt).
  3. EODHD /fundamentals for each survivor (10 units each, cached 7 days).
  4. Sector median trailing PE across survivors -> criterion 11.
  5. Grade the 13-point checklist; rank by points on the criteria EODHD
     could supply (n/a earns nothing and is shown as n/a, never guessed).
  6. Markdown + JSON report in scanner/data/outputs/, optional email.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Optional

from . import eodhd
from .checklist import (GRADE_ICON, QUANT_ORDER, CompanyChecklist, build,
                        load_config, render_card, sector_medians, trailing_pe)
from .bulk_fetch import fetch_price_stats
from .emailer import send_email
from .opportunity import Opportunity, rank_opportunities
from .pdf_report import build_html, email_html, render_pdf

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path(__file__).parent / "data" / "outputs"
SCREENER_PAGE = 100
SCREENER_MAX_OFFSET = 900   # EODHD caps offset at 999


# ---------------------------------------------------------------------------
# Step 1-2: universe via the EODHD screener
# ---------------------------------------------------------------------------

def _screen_band(exchange: str, lo: float, hi: float, extra: list) -> list[dict]:
    """All screener rows with lo <= market cap < hi, splitting the band if it
    would overflow EODHD's 1,000-row offset cap."""
    filters = [["exchange", "=", exchange.lower()],
               ["market_capitalization", ">=", lo],
               ["market_capitalization", "<", hi]] + extra
    rows: list[dict] = []
    for offset in range(0, SCREENER_MAX_OFFSET + 1, SCREENER_PAGE):
        page = eodhd.screener(filters, sort="market_capitalization.desc",
                              limit=SCREENER_PAGE, offset=offset)
        rows.extend(page)
        if len(page) < SCREENER_PAGE:
            return rows
    # Band overflowed: split geometrically and retry each half.
    mid = (lo * hi) ** 0.5
    logger.info("Screener band %.0f-%.0f overflowed, splitting at %.0f", lo, hi, mid)
    return _screen_band(exchange, lo, mid, extra) + _screen_band(exchange, mid, hi, extra)


def prefilter_universe(hcfg: dict) -> list[dict]:
    extra = [["earnings_share", ">", 0]] if hcfg.get("require_positive_eps", True) else []
    rows = _screen_band(hcfg["exchange"], hcfg["min_market_cap_aud"], hcfg["max_market_cap_aud"], extra)
    seen, out = set(), []
    excluded = set(hcfg.get("exclude_sectors") or [])
    excl_ind = tuple(hcfg.get("exclude_industries") or [])
    min_value = hcfg.get("min_avg_daily_value_aud", 0)
    for r in rows:
        code = r.get("code")
        if not code or code in seen:
            continue
        seen.add(code)
        if r.get("sector") in excluded or str(r.get("industry") or "").startswith(excl_ind):
            continue
        px, vol = eodhd.num(r.get("adjusted_close")), eodhd.num(r.get("avgvol_200d"))
        if px is None or vol is None or px * vol < min_value:
            continue
        out.append(r)
    logger.info("Screener: %d ASX rows, %d after sector/liquidity filters", len(seen), len(out))
    return out


# ---------------------------------------------------------------------------
# Step 3: fundamentals
# ---------------------------------------------------------------------------

def fetch_fundamentals(symbols: list[str], workers: int = 6) -> tuple[dict[str, dict], dict[str, str]]:
    got: dict[str, dict] = {}
    failed: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(eodhd.fundamentals, s): s for s in symbols}
        for i, fut in enumerate(as_completed(futs), 1):
            s = futs[fut]
            try:
                got[s] = fut.result()
            except eodhd.EODHDError as exc:
                failed[s] = str(exc)
            if i % 50 == 0 or i == len(symbols):
                print(f"  fundamentals {i}/{len(symbols)}")
    return got, failed


# ---------------------------------------------------------------------------
# Step 4-5: score
# ---------------------------------------------------------------------------

def score_all(funds: dict[str, dict], cfg: dict) -> tuple[list[CompanyChecklist], str]:
    hcfg = cfg["hunt"]
    try:
        aud_usd, fx_asof = eodhd.fx_rate("AUD", "USD")
        fx_note = f"AUDUSD {aud_usd:.4f} (EODHD, {fx_asof})"
    except eodhd.EODHDError as exc:
        aud_usd, fx_asof, fx_note = None, "", f"AUDUSD unavailable from EODHD ({exc}) — market-cap criterion n/a"
        logger.warning(fx_note)

    def sector_of(f: dict) -> str:
        g = f.get("General") or {}
        return str(g.get("Sector") or g.get("GicSector") or "")

    medians = sector_medians([(sector_of(f), trailing_pe(f)) for f in funds.values()],
                             hcfg.get("min_peers_for_median", 5))
    out = []
    for sym, f in funds.items():
        med = medians.get(sector_of(f))
        out.append(build(sym, f, cfg, aud_usd=aud_usd, fx_asof=fx_asof,
                         sector_median_pe=med[0] if med else None,
                         peer_count=med[1] if med else 0))
    return out, fx_note


def rank(cls: list[CompanyChecklist], min_scored: int) -> list[CompanyChecklist]:
    eligible = [c for c in cls if len(c.scored) >= min_scored]
    return sorted(eligible, key=lambda c: (c.pct or 0, c.points, len(c.scored)), reverse=True)


# ---------------------------------------------------------------------------
# Step 6: report
# ---------------------------------------------------------------------------

SHORT = {"sales_cagr": "Sales", "gross_margin": "GM", "eps_cagr": "EPS", "roe": "ROE",
         "roic": "ROIC", "analysts": "Anl", "pe_discount": "PE disc", "peg": "PEG",
         "market_cap_usd_bn": "US$bn"}


def _row(i: int, c: CompanyChecklist) -> str:
    cells = []
    for k in QUANT_ORDER:
        m = c.metrics[k]
        cells.append(f"{GRADE_ICON[m.grade]} {m.display}")
    pct = f"{c.pct:.0f}%" if c.pct is not None else "n/a"
    return (f"| {i} | {eodhd.display_ticker(c.symbol)} | {c.name[:28]} | {c.sector[:18]} | "
            f"**{c.points}/{c.max_points}** ({pct}) | " + " | ".join(cells) + " |")


def build_markdown(ranked: list[CompanyChecklist], meta: dict, cfg: dict,
                   opps: Optional[list[Opportunity]] = None) -> str:
    top_n = cfg["hunt"].get("top_n", 30)
    top = [o.checklist for o in opps[:top_n]] if opps else ranked[:top_n]
    lines = [
        f"# 100-Bagger Hunt (ASX) — {meta['date']}",
        "",
        "Checklist: *How to hunt for 100-baggers* (Mayer's 100 Baggers). "
        "🟢 Great · 🟩 Good · 🟨 Meh · 🟥 Yikes · ⬜ n/a (EODHD had no figure — not guessed).",
        "",
        "## Run summary",
        f"- **Data source:** EODHD only ({meta['eodhd_requests']} API requests, "
        f"{meta['disk_cache_hits']} fundamentals from 7-day cache)",
        f"- **ASX names after pre-filter:** {meta['prefiltered']:,} "
        f"(mkt cap A${cfg['hunt']['min_market_cap_aud']/1e6:,.0f}m–A${cfg['hunt']['max_market_cap_aud']/1e9:,.0f}bn, "
        f"EPS > 0, excluded sectors: {', '.join(cfg['hunt'].get('exclude_sectors') or ['none'])}; "
        f"excluded industries: {', '.join(cfg['hunt'].get('exclude_industries') or ['none'])})",
        f"- **Scored:** {meta['scored']:,} · **Ranked** (≥{cfg['hunt']['min_scored_criteria']} of 9 criteria with data): {meta['ranked']:,}",
        f"- **FX:** {meta['fx_note']}",
        f"- **Fundamentals failures:** {meta['failed']}",
        "",
    ]
    if opps:
        lines += [
            f"## Top {min(top_n, len(opps))} opportunities (60% quality + 40% price)",
            "",
            "| # | Ticker | Company | Score | Quality | Price | Bucket | Price vs 52w high (EODHD) |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for i, o in enumerate(opps[:top_n], 1):
            ps = o.price_stats
            px = f"A${ps.current_price:,.3g}, {ps.pct_below_high:.0f}% below high" if ps else "n/a"
            lines.append(f"| {i} | {eodhd.display_ticker(o.checklist.symbol)} | {o.checklist.name[:28]} | "
                         f"**{o.score:.0f}** | {o.quality:.1f}/3 | {o.price:.1f}/3 | {o.bucket} | {px} |")
        lines.append("")
    lines += [
        f"## Checklist grades — same {len(top)} companies",
        "",
        "| # | Ticker | Company | Sector | Score | " + " | ".join(SHORT[k] for k in QUANT_ORDER) + " |",
        "|---|---|---|---|---|" + "---|" * len(QUANT_ORDER),
    ]
    lines += [_row(i, c) for i, c in enumerate(top, 1)]
    lines += ["", "## Checklist cards (top 10)", ""]
    for c in top[:10]:
        lines.append(render_card(c, cfg))
    lines += [
        "---",
        "*Quantitative screen only — criteria 6, 7, 8 and 10 need your judgement. "
        "Every number above is from EODHD; anything EODHD lacked is shown as n/a. Not financial advice.*",
    ]
    return "\n".join(lines)


def write_report(ranked: list[CompanyChecklist], meta: dict, cfg: dict,
                 opps: Optional[list[Opportunity]] = None) -> tuple[Path, Path, str]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{meta['date']}_checklist_hunt"
    json_path = OUTPUT_DIR / f"{stem}.json"
    json_path.write_text(json.dumps({
        "metadata": meta,
        "opportunities": [{"symbol": o.checklist.symbol, "score": round(o.score, 1),
                           "quality": round(o.quality, 2), "price": round(o.price, 2),
                           "bucket": o.bucket, "strengths": o.strengths, "watch_outs": o.watch_outs,
                           "price_stats": o.price_stats.__dict__ if o.price_stats else None}
                          for o in (opps or [])],
        "ranked": [c.to_dict() for c in ranked]}, indent=2, default=str))
    md = build_markdown(ranked, meta, cfg, opps)
    md_path = OUTPUT_DIR / f"{stem}.md"
    md_path.write_text(md)
    return json_path, md_path, md


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def single_tickers(tickers: list[str], cfg: dict) -> None:
    """Checklist cards for named tickers. PE-discount uses sector peers from
    the EODHD screener (same pre-filter as the hunt) when available."""
    syms = [eodhd.symbol(t) for t in tickers]
    funds, failed = fetch_fundamentals(syms)
    for s, why in failed.items():
        print(f"{s}: {why}")
    # Peer medians: positive-PE ASX names in each requested sector, via screener rows.
    peer_pes: list[tuple[str, Optional[float]]] = []
    sectors = {str((f.get("General") or {}).get("Sector") or "") for f in funds.values()}
    for sector in filter(None, sectors):
        rows = _screen_band(cfg["hunt"]["exchange"], cfg["hunt"]["min_market_cap_aud"],
                            cfg["hunt"]["max_market_cap_aud"],
                            [["earnings_share", ">", 0], ["sector", "=", sector]])
        for r in rows:
            px, eps = eodhd.num(r.get("adjusted_close")), eodhd.num(r.get("earnings_share"))
            peer_pes.append((sector, px / eps if px and eps and eps > 0 else None))
    medians = sector_medians(peer_pes, cfg["hunt"].get("min_peers_for_median", 5))
    try:
        aud_usd, fx_asof = eodhd.fx_rate("AUD", "USD")
    except eodhd.EODHDError:
        aud_usd, fx_asof = None, ""
    for s, f in funds.items():
        sector = str((f.get("General") or {}).get("Sector") or "")
        med = medians.get(sector)
        cl = build(s, f, cfg, aud_usd=aud_usd, fx_asof=fx_asof,
                   sector_median_pe=med[0] if med else None, peer_count=med[1] if med else 0)
        print(render_card(cl, cfg))
    print(f"_EODHD requests: {eodhd.stats['requests']}. Peer PE = screener price / EPS._")


def main() -> None:
    ap = argparse.ArgumentParser(description="100x-checklist hunt over the ASX (EODHD data only).")
    ap.add_argument("--ticker", action="append", help="Show the checklist card for this ticker (repeatable)")
    ap.add_argument("--limit", type=int, default=0, help="Only score the first N pre-filtered names")
    ap.add_argument("--no-email", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    if not eodhd.is_configured():
        raise SystemExit("EODHD_API_TOKEN is not set. This bot only uses EODHD data — refusing to run without it.")

    if args.ticker:
        single_tickers(args.ticker, cfg)
        return

    t0 = time.time()
    print("Step 1/4 — EODHD screener pre-filter...")
    rows = prefilter_universe(cfg["hunt"])
    if args.limit:
        rows = rows[: args.limit]
    syms = [f"{r['code']}.{cfg['hunt']['exchange']}" for r in rows]
    print(f"  {len(syms)} names to score\n")

    print("Step 2/4 — EODHD fundamentals...")
    funds, failed = fetch_fundamentals(syms)

    print("Step 3/4 — grading the 100x checklist...")
    cls, fx_note = score_all(funds, cfg)
    ranked = rank(cls, cfg["hunt"].get("min_scored_criteria", 6))

    opps, not_ranked = rank_opportunities(cls, cfg["hunt"].get("opportunity"))
    print(f"  {len(opps)} opportunities ranked ({len(not_ranked)} not ranked: thin data or quality gate)")

    print("Step 4/4 — EODHD prices for the top names, then report...")
    top_n = cfg["hunt"].get("top_n", 30)
    stats = fetch_price_stats([o.checklist.symbol for o in opps[:top_n]])
    for o in opps[:top_n]:
        o.price_stats = stats.get(o.checklist.symbol)

    meta = {
        "date": date.today().isoformat(),
        "source": eodhd.SOURCE,
        "prefiltered": len(syms),
        "scored": len(cls),
        "ranked": len(ranked),
        "opportunities": len(opps),
        "failed": len(failed),
        "failures": failed,
        "fx_note": fx_note,
        "eodhd_requests": eodhd.stats["requests"],
        "disk_cache_hits": eodhd.stats["disk_hits"],
        "runtime_seconds": round(time.time() - t0, 1),
    }
    json_path, md_path, md = write_report(ranked, meta, cfg, opps)
    print(f"  JSON: {json_path}\n  MD  : {md_path}")

    pdf_path: Optional[Path] = OUTPUT_DIR / f"{meta['date']}_100_bagger_hunt.pdf"
    try:
        render_pdf(build_html(opps, cls, meta, cfg), pdf_path)
        print(f"  PDF : {pdf_path}")
    except Exception as exc:  # report the failure in the email, never hide it
        logger.error("PDF render failed: %s", exc)
        pdf_path = None

    if not args.no_email:
        lead = ""
        if opps:
            o = opps[0]
            lead = f" — #1 {eodhd.display_ticker(o.checklist.symbol)} ({o.score:.0f})"
        send_email(md, f"100-Bagger Hunt (ASX) — {meta['date']} ({len(opps)} opportunities){lead}",
                   html_body=email_html(opps, meta, pdf_path is not None),
                   attachments=[pdf_path] if pdf_path else None)

if __name__ == "__main__":
    main()
