"""EODHD is the only market-data source for the scanner (see CLAUDE.md).

Fails if anyone brings back yfinance, FMP, Alpha Vantage, Yahoo price
endpoints or a made-up fallback in scanner/ or its workflow.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

BANNED = [
    (re.compile(r"^\s*(import|from)\s+yfinance\b", re.M), "imports yfinance"),
    (re.compile(r"financialmodelingprep\.com"), "calls FMP"),
    (re.compile(r"alphavantage\.co"), "calls Alpha Vantage"),
    (re.compile(r"finance\.yahoo\.com/v\d+/finance/(chart|quote|quoteSummary)"), "calls Yahoo prices"),
    (re.compile(r"[Ss]ynthetic placeholder"), "invents placeholder prices"),
]


def test_scanner_has_no_second_market_data_source():
    hits = []
    for p in (REPO / "scanner").rglob("*.py"):
        text = p.read_text(encoding="utf-8")
        hits += [f"{p.relative_to(REPO)}: {why}" for rx, why in BANNED if rx.search(text)]
    assert not hits, "Market data must come from scanner/eodhd.py only:\n" + "\n".join(hits)


def test_scanner_requirements_do_not_install_yfinance():
    assert "yfinance" not in (REPO / "scanner" / "requirements.txt").read_text()


def test_scanner_workflow_gets_the_eodhd_token():
    text = (REPO / ".github" / "workflows" / "hundred_bagger_scan.yml").read_text()
    assert "EODHD_API_TOKEN: ${{ secrets.EODHD_API_TOKEN }}" in text
    assert "yfinance" not in text


def test_data_rules_doc_exists():
    text = (REPO / "CLAUDE.md").read_text()
    assert "EODHD" in text and "never guess" in text.lower()
