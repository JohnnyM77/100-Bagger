"""
checklist.py — the 13-point "100x checklist" computed from EODHD data.

Source: "How to hunt for 100-baggers, an investment check-list" (Kevin,
100 Bagger Hunting), built on Christopher Mayer's *100 Baggers*.
Thresholds live in config/checklist.yaml.

Quantitative criteria (1-5, 9, 11-13) are computed from the EODHD
fundamentals record and graded Yikes/Meh/Good/Great = 0/1/2/3. The four
judgement criteria (6 capital allocation, 7 incentives, 8 moat, 10 culture)
are never graded by the bot: it shows the EODHD evidence and leaves the
call to a human.

Every metric is either a number derived from EODHD fields, or ``None`` with
a reason. Nothing is estimated, defaulted or back-filled.
"""

from __future__ import annotations

import datetime as dt
import statistics
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from .eodhd import num

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "checklist.yaml"
GRADES = ["Yikes", "Meh", "Good", "Great"]
GRADE_ICON = {"Yikes": "🟥", "Meh": "🟨", "Good": "🟩", "Great": "🟢", None: "⬜"}

# ROIC is not graded when invested capital is a sliver of total assets: the
# ratio then measures the denominator, not the business (WAA showed 2,816%).
MIN_IC_SHARE_OF_ASSETS = 0.05

QUANT_ORDER = [
    "sales_cagr", "gross_margin", "eps_cagr", "roe", "roic",
    "analysts", "pe_discount", "peg", "market_cap_usd_bn",
]


def load_config(path: Path = CONFIG_PATH) -> dict:
    return yaml.safe_load(path.read_text())


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Metric:
    key: str
    label: str
    value: Optional[float]
    display: str
    grade: Optional[str]        # Yikes / Meh / Good / Great / None (= n/a)
    points: int
    basis: str                  # how it was computed, or why it is n/a


@dataclass
class CompanyChecklist:
    symbol: str
    name: str
    sector: str
    industry: str
    currency: str
    fiscal_year_end: str
    latest_fy: Optional[str]
    market_cap: Optional[float]
    trailing_pe: Optional[float]
    metrics: dict[str, Metric] = field(default_factory=dict)
    evidence: dict[str, str] = field(default_factory=dict)  # for the qualitative items
    data_as_of: str = ""
    description: str = ""

    @property
    def scored(self) -> list[Metric]:
        return [m for m in self.metrics.values() if m.grade is not None]

    @property
    def points(self) -> int:
        return sum(m.points for m in self.scored)

    @property
    def max_points(self) -> int:
        return 3 * len(self.scored)

    @property
    def pct(self) -> Optional[float]:
        return 100.0 * self.points / self.max_points if self.max_points else None

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(points=self.points, max_points=self.max_points, pct=self.pct,
                 scored_criteria=len(self.scored))
        return d


# ---------------------------------------------------------------------------
# Grading
# ---------------------------------------------------------------------------

def grade(value: Optional[float], rule: dict) -> Optional[str]:
    """Grade a value against a config rule. ``None`` stays ``None`` (n/a)."""
    if value is None:
        return None
    if rule["better"] == "higher":
        if value > rule["great"]:
            return "Great"
        if value > rule["good"]:
            return "Good"
        if value >= rule["meh"]:
            return "Meh"
        return "Yikes"
    # lower is better
    if value <= rule["great"]:
        return "Great"
    if value <= rule["good"]:
        return "Good"
    if value <= rule["meh"]:
        return "Meh"
    return "Yikes"


def _metric(key: str, rule: dict, value: Optional[float], display: str, basis: str) -> Metric:
    g = grade(value, rule)
    return Metric(key=key, label=rule["label"], value=value,
                  display=display if value is not None else "n/a",
                  grade=g, points=GRADES.index(g) if g else 0, basis=basis)


def _pct(v: Optional[float]) -> str:
    return f"{v:.1f}%" if v is not None else "n/a"


# ---------------------------------------------------------------------------
# EODHD record helpers
# ---------------------------------------------------------------------------

def _yearly(f: dict, statement: str) -> list[tuple[str, dict]]:
    """Yearly rows of a Financials statement, oldest first."""
    rows = (((f.get("Financials") or {}).get(statement) or {}).get("yearly")) or {}
    out = [(str(k)[:10], v) for k, v in rows.items() if isinstance(v, dict)]
    return sorted(out, key=lambda kv: kv[0])


def _years_between(a: str, b: str) -> float:
    da, db = dt.date.fromisoformat(a), dt.date.fromisoformat(b)
    return (db - da).days / 365.25


def cagr_series(points: list[tuple[str, float]], max_years: int, min_years: int
                ) -> tuple[Optional[float], str]:
    """CAGR (%) between the latest point and the one ~max_years earlier.

    Points are (date, value) oldest first. Requires both ends positive and a
    span of at least ``min_years``. Returns (value, basis-or-reason).
    """
    pts = [(d, v) for d, v in points if v is not None]
    if len(pts) < 2:
        return None, "fewer than 2 fiscal years in EODHD"
    end_d, end_v = pts[-1]
    start = None
    for d, v in pts:
        if _years_between(d, end_d) <= max_years + 0.25:
            start = (d, v)
            break
    if start is None:
        return None, "no start year in range"
    span = _years_between(start[0], end_d)
    if span < min_years - 0.25:
        return None, f"only {span:.0f}y of history in EODHD (need {min_years})"
    if start[1] <= 0 or end_v <= 0:
        return None, f"negative/zero at an end ({start[0][:4]}: {start[1]:,.3g}, {end_d[:4]}: {end_v:,.3g}) — CAGR undefined"
    rate = ((end_v / start[1]) ** (1 / span) - 1) * 100
    return rate, f"FY{start[0][:4]}→FY{end_d[:4]} ({span:.0f}y)"


# ---------------------------------------------------------------------------
# Metric calculations
# ---------------------------------------------------------------------------

def sales_cagr(f: dict) -> tuple[Optional[float], str]:
    pts = [(d, num(r.get("totalRevenue"))) for d, r in _yearly(f, "Income_Statement")]
    return cagr_series(pts, max_years=10, min_years=3)


def gross_margin(f: dict) -> tuple[Optional[float], str]:
    rows = _yearly(f, "Income_Statement")
    if not rows:
        return None, "no income statement in EODHD"
    d, r = rows[-1]
    gp, rev = num(r.get("grossProfit")), num(r.get("totalRevenue"))
    if gp is None or not rev or rev <= 0:
        return None, f"FY{d[:4]} gross profit or revenue missing in EODHD"
    gm = gp / rev * 100
    if not 0 <= gm <= 100:
        return None, (f"FY{d[:4]} grossProfit/totalRevenue = {gm:,.0f}% — outside 0–100%, "
                      "so EODHD's revenue line doesn't fit this business; not graded")
    return gm, f"FY{d[:4]} grossProfit / totalRevenue"


def eps_points(f: dict) -> list[tuple[str, Optional[float]]]:
    """Annual EPS = netIncome / balance-sheet shares outstanding (same date)."""
    bs = dict(_yearly(f, "Balance_Sheet"))
    out = []
    for d, r in _yearly(f, "Income_Statement"):
        ni = num(r.get("netIncome"))
        sh = num((bs.get(d) or {}).get("commonStockSharesOutstanding"))
        out.append((d, ni / sh if ni is not None and sh and sh > 0 else None))
    return out


def eps_cagr(f: dict) -> tuple[Optional[float], str]:
    v, basis = cagr_series(eps_points(f), max_years=5, min_years=3)
    return v, ("EPS = netIncome / shares; " + basis) if v is not None else basis


def roe(f: dict) -> tuple[Optional[float], str]:
    v = num((f.get("Highlights") or {}).get("ReturnOnEquityTTM"))
    return (v * 100, "Highlights.ReturnOnEquityTTM") if v is not None else (None, "EODHD has no ROE")


def roic(f: dict) -> tuple[Optional[float], str]:
    inc, bs = _yearly(f, "Income_Statement"), dict(_yearly(f, "Balance_Sheet"))
    if not inc:
        return None, "no income statement in EODHD"
    d, r = inc[-1]
    ebit = num(r.get("operatingIncome"))
    if ebit is None:
        ebit = num(r.get("ebit"))
    if ebit is None:
        return None, f"FY{d[:4]} operating income missing in EODHD"
    pretax, tax = num(r.get("incomeBeforeTax")), num(r.get("incomeTaxExpense"))
    if pretax and pretax > 0 and tax is not None:
        rate = min(max(tax / pretax, 0.0), 0.5)
        tax_note = f"tax {rate:.0%} (reported)"
    else:
        rate, tax_note = 0.0, "tax 0% (no positive pre-tax profit)"
    nopat = ebit * (1 - rate)

    def invested(row: dict) -> Optional[float]:
        eq = num(row.get("totalStockholderEquity"))
        debt = num(row.get("shortLongTermDebtTotal"))
        if debt is None:
            st, lt = num(row.get("shortTermDebt")), num(row.get("longTermDebt"))
            debt = (st or 0) + (lt or 0) if (st is not None or lt is not None) else None
        cash = num(row.get("cashAndShortTermInvestments"))
        if cash is None:
            cash = num(row.get("cash"))
        if eq is None or debt is None or cash is None:
            return None
        return eq + debt - cash

    dates = sorted(bs)
    ics = [invested(bs[x]) for x in dates[-2:]] if dates else []
    ics = [x for x in ics if x is not None]
    if not ics:
        return None, "equity/debt/cash missing in EODHD balance sheet"
    ic = sum(ics) / len(ics)
    if ic <= 0:
        return None, "invested capital ≤ 0 (net cash exceeds equity+debt) — ROIC not meaningful"
    assets = num(bs[dates[-1]].get("totalAssets"))
    if assets and assets > 0 and ic < MIN_IC_SHARE_OF_ASSETS * assets:
        return None, (f"invested capital is {ic / assets:.0%} of total assets (net cash ≈ equity + debt) "
                      "— ROIC not meaningful, not graded")
    return nopat / ic * 100, f"FY{d[:4]} NOPAT ({tax_note}) / avg invested capital ({len(ics)}y)"


def analyst_count(f: dict) -> tuple[Optional[float], str]:
    ar = f.get("AnalystRatings")
    if not isinstance(ar, dict):
        return None, "EODHD has no analyst-ratings record (often means few/no analysts — check manually)"
    keys = ["StrongBuy", "Buy", "Hold", "Sell", "StrongSell"]
    vals = [num(ar.get(k)) for k in keys]
    if all(v is None for v in vals):
        return None, "EODHD analyst counts empty"
    return float(sum(v or 0 for v in vals)), "AnalystRatings StrongBuy+Buy+Hold+Sell+StrongSell"


def trailing_pe(f: dict) -> Optional[float]:
    v = num((f.get("Valuation") or {}).get("TrailingPE"))
    if v is None:
        v = num((f.get("Highlights") or {}).get("PERatio"))
    return v if v is not None and v > 0 else None


def peg(f: dict, eps_growth: Optional[float]) -> tuple[Optional[float], str]:
    v = num((f.get("Highlights") or {}).get("PEGRatio"))
    if v is not None and v > 0:
        return v, "Highlights.PEGRatio (EODHD, forward)"
    pe = trailing_pe(f)
    if pe and eps_growth and eps_growth > 0:
        return pe / eps_growth, "trailing PE / historical EPS CAGR (no forward PEG in EODHD)"
    return None, "no EODHD PEG and no positive PE + EPS growth to derive one"


def market_cap(f: dict) -> Optional[float]:
    return num((f.get("Highlights") or {}).get("MarketCapitalization"))


# ---------------------------------------------------------------------------
# Qualitative evidence (never graded)
# ---------------------------------------------------------------------------

def evidence(f: dict) -> dict[str, str]:
    ev: dict[str, str] = {}
    ss = f.get("SharesStats") or {}
    ins = num(ss.get("PercentInsiders"))
    ev["insider_ownership"] = f"{ins:.1f}% held by insiders (EODHD SharesStats)" if ins is not None else "n/a in EODHD"

    officers = ((f.get("General") or {}).get("Officers") or {})
    founders = [o.get("Name", "").strip() for o in officers.values()
                if isinstance(o, dict) and "founder" in str(o.get("Title", "")).lower()]
    ev["founder_led"] = ("Founder among officers: " + ", ".join(founders)) if founders else "No officer titled founder in EODHD"

    bs = _yearly(f, "Balance_Sheet")
    sh = [(d, num(r.get("commonStockSharesOutstanding"))) for d, r in bs]
    sh = [(d, v) for d, v in sh if v]
    if len(sh) >= 2:
        start = next(((d, v) for d, v in sh if _years_between(d, sh[-1][0]) <= 5.25), sh[0])
        chg = (sh[-1][1] / start[1] - 1) * 100
        ev["share_count_change"] = f"Shares outstanding {chg:+.1f}% FY{start[0][:4]}→FY{sh[-1][0][:4]} (dilution/buybacks)"
    else:
        ev["share_count_change"] = "n/a in EODHD"

    rows = _yearly(f, "Cash_Flow")[-5:]
    fcf = [(d[:4], num(r.get("freeCashFlow"))) for d, r in rows]
    if any(v is not None for _, v in fcf):
        ev["free_cash_flow"] = "FCF by FY: " + ", ".join(
            f"{y}: {v/1e6:,.1f}m" if v is not None else f"{y}: n/a" for y, v in fcf)
    return ev


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(sym: str, f: dict, cfg: dict, *, aud_usd: Optional[float] = None,
          fx_asof: str = "", sector_median_pe: Optional[float] = None,
          peer_count: int = 0) -> CompanyChecklist:
    """Compute the checklist for one company from its EODHD fundamentals record.

    ``sector_median_pe`` is supplied by the hunt (median trailing PE of
    positive-PE sector peers in the scanned set); without it, criterion 11 is
    n/a.
    """
    rules = cfg["criteria"]
    g = f.get("General") or {}
    inc = _yearly(f, "Income_Statement")
    cl = CompanyChecklist(
        symbol=sym,
        name=str(g.get("Name") or sym),
        sector=str(g.get("Sector") or g.get("GicSector") or ""),
        industry=str(g.get("Industry") or ""),
        currency=str(g.get("CurrencyCode") or ""),
        fiscal_year_end=str(g.get("FiscalYearEnd") or ""),
        latest_fy=inc[-1][0] if inc else None,
        market_cap=market_cap(f),
        trailing_pe=trailing_pe(f),
        data_as_of=str(g.get("UpdatedAt") or ""),
        description=str(g.get("Description") or "").strip(),
    )

    v, b = sales_cagr(f)
    cl.metrics["sales_cagr"] = _metric("sales_cagr", rules["sales_cagr"], v, _pct(v), b)
    v, b = gross_margin(f)
    cl.metrics["gross_margin"] = _metric("gross_margin", rules["gross_margin"], v, _pct(v), b)
    eps_g, b = eps_cagr(f)
    cl.metrics["eps_cagr"] = _metric("eps_cagr", rules["eps_cagr"], eps_g, _pct(eps_g), b)
    v, b = roe(f)
    cl.metrics["roe"] = _metric("roe", rules["roe"], v, _pct(v), b)
    v, b = roic(f)
    cl.metrics["roic"] = _metric("roic", rules["roic"], v, _pct(v), b)
    v, b = analyst_count(f)
    cl.metrics["analysts"] = _metric("analysts", rules["analysts"], v,
                                     f"{v:.0f}" if v is not None else "n/a", b)

    pe = cl.trailing_pe
    if pe is None:
        v, b = None, "no positive trailing PE in EODHD"
    elif sector_median_pe is None:
        v, b = None, "not enough sector peers with a positive PE to form a median"
    else:
        v = (1 - pe / sector_median_pe) * 100
        b = f"PE {pe:.1f} vs {cl.sector} median {sector_median_pe:.1f} ({peer_count} peers)"
    cl.metrics["pe_discount"] = _metric("pe_discount", rules["pe_discount"], v, _pct(v), b)

    v, b = peg(f, eps_g)
    cl.metrics["peg"] = _metric("peg", rules["peg"], v, f"{v:.2f}" if v is not None else "n/a", b)

    mc = cl.market_cap
    if mc is None:
        v, b = None, "EODHD has no market cap"
    elif cl.currency == "USD":
        v, b = mc / 1e9, "Highlights.MarketCapitalization (USD)"
    elif aud_usd is not None and cl.currency == "AUD":
        v, b = mc * aud_usd / 1e9, f"A${mc/1e6:,.0f}m × AUDUSD {aud_usd:.4f} (EODHD, {fx_asof})"
    else:
        v, b = None, f"no EODHD FX rate for {cl.currency or '?'}→USD"
    cl.metrics["market_cap_usd_bn"] = _metric("market_cap_usd_bn", rules["market_cap_usd_bn"], v,
                                              f"{v:.2f}" if v is not None else "n/a", b)

    cl.evidence = evidence(f)
    return cl


def sector_medians(pes: list[tuple[str, Optional[float]]], min_peers: int) -> dict[str, tuple[float, int]]:
    """{sector: (median PE, peer count)} from (sector, trailing PE) pairs."""
    by: dict[str, list[float]] = {}
    for sector, pe in pes:
        if sector and pe is not None and pe > 0:
            by.setdefault(sector, []).append(pe)
    return {s: (statistics.median(v), len(v)) for s, v in by.items() if len(v) >= min_peers}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_card(cl: CompanyChecklist, cfg: dict) -> str:
    """One company's full checklist as markdown."""
    from .eodhd import display_ticker
    mc = f"{cl.currency} {cl.market_cap/1e6:,.0f}m" if cl.market_cap else "n/a"
    pct = f"{cl.pct:.0f}%" if cl.pct is not None else "n/a"
    lines = [
        f"### {display_ticker(cl.symbol)} — {cl.name}",
        f"*{cl.sector} / {cl.industry} · Mkt cap {mc} · FY ends {cl.fiscal_year_end} · "
        f"latest FY {cl.latest_fy or 'n/a'} · EODHD record updated {cl.data_as_of or 'n/a'}*",
        "",
        f"**Score: {cl.points}/{cl.max_points} ({pct}) on {len(cl.scored)} of {len(QUANT_ORDER)} quantitative criteria**",
        "",
        "| # | Criterion | Value | Grade | Basis (all EODHD) |",
        "|---|-----------|-------|-------|-------------------|",
    ]
    numbering = {"sales_cagr": 1, "gross_margin": 2, "eps_cagr": 3, "roe": 4, "roic": 5,
                 "analysts": 9, "pe_discount": 11, "peg": 12, "market_cap_usd_bn": 13}
    for key in QUANT_ORDER:
        m = cl.metrics[key]
        lines.append(f"| {numbering[key]} | {m.label} | {m.display} | "
                     f"{GRADE_ICON[m.grade]} {m.grade or 'n/a'} | {m.basis} |")
    lines += ["", "**Judgement calls (not graded by the bot):**", ""]
    q = cfg.get("qualitative", {})
    lines += [
        f"- 6. {q.get('capital_allocation', 'Capital allocation')} — evidence: "
        f"{cl.evidence.get('share_count_change', 'n/a')}; {cl.evidence.get('free_cash_flow', 'FCF n/a')}",
        f"- 7. {q.get('incentives', 'Incentives')} — evidence: "
        f"{cl.evidence.get('insider_ownership', 'n/a')}; {cl.evidence.get('founder_led', '')}",
        f"- 8. {q.get('moat', 'Moat')} — evidence: see ROIC (#5) and gross margin (#2) above",
        f"- 10. {q.get('culture', 'Culture')} — no data; read reviews, AGM, founder letters",
        "",
    ]
    return "\n".join(lines)
