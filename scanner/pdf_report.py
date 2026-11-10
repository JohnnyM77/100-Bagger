"""
pdf_report.py — the hunt's PDF report and the short HTML email that carries it.

The email is a glance (top 10 table, inline styles only so mail clients
render it); the PDF is everything: ranked opportunities, a checklist card
per top name, and the full scored list. Rendered with Playwright Chromium
(``PW_CHROMIUM_PATH`` overrides the browser binary). Every figure shown is
an EODHD figure or arithmetic on one; n/a stays n/a.
"""

from __future__ import annotations

import html
import logging
import os
from pathlib import Path
from typing import Optional

from .checklist import QUANT_ORDER, CompanyChecklist
from .eodhd import display_ticker
from .opportunity import Opportunity

logger = logging.getLogger(__name__)

GRADE_BG = {"Great": "#1f8a4c", "Good": "#7cc48f", "Meh": "#f2d36b", "Yikes": "#e07a6b", None: "#e6e6e6"}
GRADE_FG = {"Great": "#fff", "Good": "#10331c", "Meh": "#4a3b00", "Yikes": "#fff", None: "#666"}
NUM = {"sales_cagr": 1, "gross_margin": 2, "eps_cagr": 3, "roe": 4, "roic": 5,
       "analysts": 9, "pe_discount": 11, "peg": 12, "market_cap_usd_bn": 13}
SHORT = {"sales_cagr": "Sales", "gross_margin": "GM", "eps_cagr": "EPS", "roe": "ROE",
         "roic": "ROIC", "analysts": "Anl", "pe_discount": "PE disc", "peg": "PEG",
         "market_cap_usd_bn": "US$bn"}

e = html.escape


def _chip(grade: Optional[str], text: str) -> str:
    return (f'<span class="chip" style="background:{GRADE_BG[grade]};color:{GRADE_FG[grade]}">'
            f"{e(text)}</span>")


def _price_line(o: Opportunity) -> str:
    ps = o.price_stats
    if ps is None:
        return "n/a"
    return (f"A${ps.current_price:,.3g} · {ps.pct_below_high:.0f}% below 52w high "
            f"({ps.last_date})")


def _mcap(cl: CompanyChecklist) -> str:
    return f"{cl.currency} {cl.market_cap/1e6:,.0f}m" if cl.market_cap else "n/a"


CSS = """
@page { size: A4; margin: 14mm 12mm 16mm; }
* { box-sizing: border-box; }
body { font-family: -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color:#1d2230; font-size:10.5px; line-height:1.4; }
h1 { font-size:24px; margin:0 0 4px; color:#12233d; }
h2 { font-size:15px; margin:22px 0 8px; color:#12233d; border-bottom:2px solid #12233d; padding-bottom:4px; }
h3 { font-size:13px; margin:0 0 2px; color:#12233d; }
.sub { color:#5b6475; margin-bottom:10px; }
.box { background:#f4f6fa; border:1px solid #dde2ec; border-radius:6px; padding:10px 12px; margin:8px 0; }
table { border-collapse:collapse; width:100%; }
th { background:#12233d; color:#fff; text-align:left; padding:5px 6px; font-size:9.5px; }
td { padding:5px 6px; border-bottom:1px solid #e3e6ee; vertical-align:top; }
tr { page-break-inside:avoid; }
.chip { display:inline-block; border-radius:4px; padding:1px 5px; font-size:9.5px; white-space:nowrap; }
.score { font-weight:700; font-size:12px; }
.bucket { font-size:9.5px; color:#3a4560; }
.card { border:1px solid #dde2ec; border-radius:8px; padding:12px; margin:12px 0; page-break-inside:avoid; }
.muted { color:#6b7385; font-size:9.5px; }
.flags { margin:4px 0 0; padding-left:16px; }
.pill { display:inline-block; background:#12233d; color:#fff; border-radius:10px; padding:2px 8px; font-size:10px; margin-left:6px; }
.small td, .small th { font-size:8.5px; padding:3px 4px; }
"""


def _summary_rows(opps: list[Opportunity], n: int) -> str:
    rows = []
    for i, o in enumerate(opps[:n], 1):
        cl = o.checklist
        rows.append(
            f"<tr><td>{i}</td><td><b>{e(display_ticker(cl.symbol))}</b><br>"
            f"<span class='muted'>{e(cl.name[:34])}</span></td>"
            f"<td>{e(cl.sector)}</td>"
            f"<td class='score'>{o.score:.0f}</td>"
            f"<td>{o.quality:.1f}/3</td><td>{o.price:.1f}/3</td>"
            f"<td class='bucket'>{e(o.bucket)}</td>"
            f"<td>{e(_price_line(o))}</td></tr>")
    return "".join(rows)


def _card(i: int, o: Opportunity, cfg: dict) -> str:
    cl = o.checklist
    rows = []
    for k in QUANT_ORDER:
        m = cl.metrics[k]
        rows.append(f"<tr><td>{NUM[k]}</td><td>{e(m.label)}</td><td>{e(m.display)}</td>"
                    f"<td>{_chip(m.grade, m.grade or 'n/a')}</td><td class='muted'>{e(m.basis)}</td></tr>")
    q = cfg.get("qualitative", {})
    ev = cl.evidence
    desc = (cl.description[:420] + "…") if len(cl.description) > 420 else cl.description
    return f"""
<div class="card">
  <h3>#{i} {e(display_ticker(cl.symbol))} — {e(cl.name)} <span class="pill">{o.score:.0f}</span></h3>
  <div class="muted">{e(cl.sector)} / {e(cl.industry)} · Mkt cap {e(_mcap(cl))} · {e(_price_line(o))} ·
  latest FY {e(cl.latest_fy or 'n/a')} · EODHD record {e(cl.data_as_of or 'n/a')}</div>
  <p style="margin:6px 0">{e(desc) if desc else '<span class="muted">No EODHD description.</span>'}</p>
  <div><b>{e(o.bucket)}</b> — quality {o.quality:.1f}/3, price {o.price:.1f}/3</div>
  <table style="margin-top:6px"><tr><th>#</th><th>Criterion</th><th>Value</th><th>Grade</th><th>Basis (EODHD)</th></tr>
  {''.join(rows)}</table>
  <div style="margin-top:6px"><b>Strengths:</b> {e('; '.join(o.strengths) or '—')}<br>
  <b>Watch-outs:</b> {e('; '.join(o.watch_outs) or '—')}</div>
  <div class="box"><b>Your judgement (not graded by the bot)</b>
  <ul class="flags">
   <li>6. {e(q.get('capital_allocation',''))}: {e(ev.get('share_count_change','n/a'))}; {e(ev.get('free_cash_flow','FCF n/a'))}</li>
   <li>7. {e(q.get('incentives',''))}: {e(ev.get('insider_ownership','n/a'))}; {e(ev.get('founder_led',''))}</li>
   <li>8. {e(q.get('moat',''))}: see gross margin (#2) and ROIC (#5)</li>
   <li>10. {e(q.get('culture',''))}: no data</li>
  </ul></div>
</div>"""


def _full_table(cls: list[CompanyChecklist]) -> str:
    head = "".join(f"<th>{SHORT[k]}</th>" for k in QUANT_ORDER)
    rows = []
    for c in cls:
        cells = "".join(f"<td>{_chip(c.metrics[k].grade, c.metrics[k].display)}</td>" for k in QUANT_ORDER)
        rows.append(f"<tr><td><b>{e(display_ticker(c.symbol))}</b></td><td>{e(c.name[:26])}</td>"
                    f"<td>{c.points}/{c.max_points}</td>{cells}</tr>")
    return (f"<table class='small'><tr><th>Ticker</th><th>Company</th><th>Pts</th>{head}</tr>"
            + "".join(rows) + "</table>")


def build_html(opps: list[Opportunity], all_cls: list[CompanyChecklist], meta: dict, cfg: dict) -> str:
    hcfg = cfg["hunt"]
    top_n = hcfg.get("top_n", 30)
    cards = "".join(_card(i, o, cfg) for i, o in enumerate(opps[:hcfg.get("cards", 10)], 1))
    ranked_all = sorted(all_cls, key=lambda c: (c.pct or 0, c.points), reverse=True)
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<h1>100-Bagger Hunt — ASX</h1>
<div class="sub">{e(meta['date'])} · checklist from <i>How to hunt for 100-baggers</i> (Mayer's <i>100 Baggers</i>) ·
all figures from EODHD</div>

<div class="box">
<b>How the ranking works.</b> Each company is graded Yikes/Meh/Good/Great (0–3) on the checklist.
<b>Quality</b> = average grade on sales growth, gross margin, EPS growth, ROE and ROIC.
<b>Price</b> = average grade on discount to sector-median P/E, PEG and small market cap.
<b>Opportunity</b> = 60% quality + 40% price, scaled to 100. A company needs quality ≥ {hcfg.get('opportunity', {}).get('min_quality', 1.8)}/3
and enough EODHD data in both pillars to be ranked. n/a lines are left out, never guessed.
</div>

<div class="box">
<b>Run:</b> {meta['prefiltered']:,} ASX names after pre-filter · {meta['scored']:,} scored ·
<b>{len(opps)} opportunities ranked</b> · {meta['eodhd_requests']:,} EODHD requests ·
{e(meta['fx_note'])}<br>
<span class="muted">Pre-filter: market cap A${hcfg['min_market_cap_aud']/1e6:,.0f}m–A${hcfg['max_market_cap_aud']/1e9:,.0f}bn, EPS &gt; 0,
liquidity ≥ A${hcfg.get('min_avg_daily_value_aud',0):,.0f}/day; excluded sectors {e(', '.join(hcfg.get('exclude_sectors') or []))};
excluded industries {e(', '.join(hcfg.get('exclude_industries') or []))}.</span>
</div>

<h2>Top {min(top_n, len(opps))} opportunities</h2>
<table><tr><th>#</th><th>Company</th><th>Sector</th><th>Score</th><th>Quality</th><th>Price</th><th>Bucket</th><th>Share price (EODHD)</th></tr>
{_summary_rows(opps, top_n)}</table>

<h2>Checklist cards — top {min(hcfg.get('cards', 10), len(opps))}</h2>
{cards}

<h2>Appendix — every company scored ({len(ranked_all)})</h2>
{_full_table(ranked_all)}

<p class="muted" style="margin-top:14px">A quantitative filter, not a recommendation. Criteria 6, 7, 8 and 10 need your own
judgement. Number of analysts is n/a because EODHD has no analyst records for ASX names. Not financial advice.</p>
</body></html>"""


def render_pdf(html_doc: str, out_path: Path) -> Path:
    from playwright.sync_api import sync_playwright
    exe = os.environ.get("PW_CHROMIUM_PATH") or None
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=exe)
        page = browser.new_page()
        page.set_content(html_doc, wait_until="load")
        page.pdf(path=str(out_path), format="A4", print_background=True,
                 display_header_footer=True, header_template="<span></span>",
                 footer_template=('<div style="font-size:8px;color:#888;width:100%;text-align:center">'
                                  '100-Bagger Hunt · EODHD data · page <span class="pageNumber"></span>'
                                  ' of <span class="totalPages"></span></div>'),
                 margin={"top": "14mm", "bottom": "16mm", "left": "12mm", "right": "12mm"})
        browser.close()
    return out_path


def email_html(opps: list[Opportunity], meta: dict, pdf_ok: bool) -> str:
    """Short, inline-styled email body (mail clients strip <style>)."""
    td = "padding:6px 8px;border-bottom:1px solid #e3e6ee;font-size:13px;"
    th = "padding:6px 8px;background:#12233d;color:#fff;text-align:left;font-size:12px;"
    rows = "".join(
        f"<tr><td style='{td}'>{i}</td><td style='{td}'><b>{e(display_ticker(o.checklist.symbol))}</b> "
        f"{e(o.checklist.name[:30])}</td><td style='{td}'><b>{o.score:.0f}</b></td>"
        f"<td style='{td}'>{e(o.bucket)}</td></tr>"
        for i, o in enumerate(opps[:10], 1))
    note = ("The full report — every checklist card and the complete scored list — is in the attached PDF."
            if pdf_ok else "<b>PDF could not be rendered this run</b>; the Markdown report is in the workflow artifacts.")
    return f"""<div style="font-family:Arial,sans-serif;color:#1d2230;max-width:720px">
<h2 style="color:#12233d;margin:0 0 4px">100-Bagger Hunt — ASX — {e(meta['date'])}</h2>
<p style="color:#5b6475;margin:0 0 12px">{len(opps)} opportunities ranked from {meta['scored']:,} companies · all figures from EODHD</p>
<table cellpadding="0" cellspacing="0" style="border-collapse:collapse;width:100%">
<tr><th style='{th}'>#</th><th style='{th}'>Company</th><th style='{th}'>Score</th><th style='{th}'>Bucket</th></tr>
{rows}</table>
<p style="font-size:13px">{note}</p>
<p style="color:#888;font-size:11px">Score = 60% quality + 40% price on the 100x checklist. Not financial advice.</p>
</div>"""
