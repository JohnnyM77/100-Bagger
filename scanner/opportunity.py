"""
opportunity.py — rank checklist results as "best opportunities to look at".

The article's conclusion: buy *quality* as *cheap* as possible, and buy
small. So the opportunity score is two averages of the checklist grades
(Yikes 0 · Meh 1 · Good 2 · Great 3), never of raw numbers:

  Quality = sales growth, gross margin, EPS growth, ROE, ROIC
  Price   = discount to sector-median PE, PEG, small market cap

  Opportunity (0-100) = (0.6 x Quality + 0.4 x Price) / 3 x 100

Only grades EODHD could support count; an n/a is left out of the average,
never scored as anything. A company needs enough graded lines in each
pillar to be ranked at all (config: hunt.opportunity), so a recent listing
with three years of history can't top the list on a handful of grades.
Quality is a gate: below ``min_quality`` a company is not an opportunity
however cheap it looks (a cheap bad business is a value trap, not a
100-bagger).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .bulk_fetch import PriceStats
from .checklist import CompanyChecklist

QUALITY_KEYS = ["sales_cagr", "gross_margin", "eps_cagr", "roe", "roic"]
PRICE_KEYS = ["pe_discount", "peg", "market_cap_usd_bn"]

DEFAULTS = {
    "quality_weight": 0.6,
    "min_quality_graded": 4,
    "min_price_graded": 2,
    "min_quality": 1.8,
}


@dataclass
class Opportunity:
    checklist: CompanyChecklist
    quality: float              # 0-3 average grade
    price: float                # 0-3 average grade
    score: float                # 0-100
    bucket: str
    strengths: list[str] = field(default_factory=list)
    watch_outs: list[str] = field(default_factory=list)
    price_stats: Optional[PriceStats] = None   # EODHD 1-year prices, top names only


def _avg(cl: CompanyChecklist, keys: list[str]) -> tuple[Optional[float], int]:
    pts = [cl.metrics[k].points for k in keys if cl.metrics[k].grade is not None]
    return (sum(pts) / len(pts), len(pts)) if pts else (None, 0)


def bucket_for(price: float) -> str:
    if price >= 2.0:
        return "Quality at a cheap price"
    if price >= 1.0:
        return "Quality at a fair price"
    return "Quality, but priced for it — watchlist"


def rank_opportunities(cls: list[CompanyChecklist], ocfg: Optional[dict] = None
                       ) -> tuple[list[Opportunity], dict[str, str]]:
    """Return (ranked opportunities, {symbol: reason not ranked})."""
    c = {**DEFAULTS, **(ocfg or {})}
    w = c["quality_weight"]
    out: list[Opportunity] = []
    skipped: dict[str, str] = {}
    for cl in cls:
        q, nq = _avg(cl, QUALITY_KEYS)
        p, np_ = _avg(cl, PRICE_KEYS)
        if nq < c["min_quality_graded"]:
            skipped[cl.symbol] = f"only {nq} of 5 quality lines have EODHD data"
            continue
        if np_ < c["min_price_graded"]:
            skipped[cl.symbol] = f"only {np_} of 3 price lines have EODHD data"
            continue
        if q < c["min_quality"]:
            skipped[cl.symbol] = f"quality {q:.1f}/3 below the {c['min_quality']} gate"
            continue
        opp = Opportunity(
            checklist=cl, quality=q, price=p,
            score=(w * q + (1 - w) * p) / 3 * 100,
            bucket=bucket_for(p),
        )
        for k in QUALITY_KEYS + PRICE_KEYS:
            m = cl.metrics[k]
            if m.grade == "Great":
                opp.strengths.append(f"{m.label} {m.display}")
            elif m.grade == "Yikes":
                opp.watch_outs.append(f"{m.label} {m.display}")
        out.append(opp)
    out.sort(key=lambda o: (o.score, o.quality, len(o.checklist.scored)), reverse=True)
    return out, skipped
