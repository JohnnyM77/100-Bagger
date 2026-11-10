"""Checklist maths on a hand-built EODHD-shaped record (no network)."""

import pytest

from scanner import eodhd
from scanner.checklist import build, grade, load_config, sector_medians

CFG = load_config()


def _record():
    years = {
        "2021-06-30": (100.0, 60.0, 10.0, 20.0, 15.0, 4.0, 100.0, 100.0, 40.0, 10.0),
        "2022-06-30": (125.0, 75.0, 13.0, 25.0, 19.0, 5.0, 115.0, 100.0, 40.0, 12.0),
        "2023-06-30": (160.0, 96.0, 17.0, 32.0, 24.0, 6.0, 135.0, 100.0, 40.0, 15.0),
        "2024-06-30": (200.0, 120.0, 22.0, 40.0, 30.0, 7.5, 160.0, 100.0, 40.0, 18.0),
        "2025-06-30": (250.0, 150.0, 28.0, 50.0, 38.0, 9.5, 190.0, 100.0, 40.0, 20.0),
    }
    inc, bs, cf = {}, {}, {}
    for d, (rev, gp, ni, op, pre, tax, eq, sh, debt, cash) in years.items():
        inc[d] = {"date": d, "totalRevenue": str(rev), "grossProfit": str(gp), "netIncome": str(ni),
                  "operatingIncome": str(op), "incomeBeforeTax": str(pre), "incomeTaxExpense": str(tax)}
        bs[d] = {"date": d, "totalStockholderEquity": str(eq), "commonStockSharesOutstanding": str(sh),
                 "shortLongTermDebtTotal": str(debt), "cashAndShortTermInvestments": str(cash)}
        cf[d] = {"date": d, "freeCashFlow": str(ni)}
    return {
        "General": {"Name": "Test Co", "Sector": "Industrials", "CurrencyCode": "AUD",
                    "FiscalYearEnd": "June", "Officers": {"0": {"Name": "A Founder", "Title": "Founder & CEO"}}},
        "Highlights": {"MarketCapitalization": 500e6, "ReturnOnEquityTTM": 0.18, "PEGRatio": None},
        "Valuation": {"TrailingPE": 10.0},
        "SharesStats": {"PercentInsiders": 30.0},
        "AnalystRatings": "NA",
        "Financials": {"Income_Statement": {"yearly": inc}, "Balance_Sheet": {"yearly": bs},
                       "Cash_Flow": {"yearly": cf}},
    }


def test_grade_bands_follow_article():
    r = CFG["criteria"]["sales_cagr"]
    assert grade(9.9, r) == "Yikes"
    assert grade(12, r) == "Meh"
    assert grade(20, r) == "Good"
    assert grade(30, r) == "Great"
    assert grade(None, r) is None
    a = CFG["criteria"]["analysts"]
    assert [grade(x, a) for x in (0, 3, 7, 12)] == ["Great", "Good", "Meh", "Yikes"]


def test_build_from_eodhd_record():
    cl = build("TST.AU", _record(), CFG, aud_usd=0.65, fx_asof="2026-11-10",
               sector_median_pe=20.0, peer_count=8)
    m = cl.metrics
    assert m["sales_cagr"].value == pytest.approx(25.7, abs=0.1)   # 100 -> 250 over 4y
    assert m["gross_margin"].value == pytest.approx(60.0)
    assert m["eps_cagr"].value == pytest.approx(29.4, abs=0.1)     # 0.10 -> 0.28 over 4y
    assert m["roe"].value == pytest.approx(18.0)
    assert m["pe_discount"].value == pytest.approx(50.0)
    assert m["market_cap_usd_bn"].value == pytest.approx(0.325)
    assert m["peg"].basis.startswith("trailing PE")
    # No analyst record in EODHD -> n/a, not 0.
    assert m["analysts"].value is None and m["analysts"].grade is None
    assert len(cl.scored) == 8
    assert "Founder" in cl.evidence["founder_led"]


def test_missing_data_is_na_never_guessed():
    rec = _record()
    rec["Financials"] = {}
    rec["Highlights"] = {}
    rec["Valuation"] = {}
    cl = build("TST.AU", rec, CFG)
    for key in ("sales_cagr", "gross_margin", "eps_cagr", "roe", "roic", "pe_discount", "peg",
                "market_cap_usd_bn"):
        assert cl.metrics[key].value is None, key
        assert cl.metrics[key].display == "n/a"
    assert cl.points == 0 and cl.max_points == 0


def test_negative_start_eps_gives_no_cagr():
    rec = _record()
    rec["Financials"]["Income_Statement"]["yearly"]["2021-06-30"]["netIncome"] = "-5"
    cl = build("TST.AU", rec, CFG)
    # Start year is negative -> CAGR undefined, reported as n/a with the reason.
    assert cl.metrics["eps_cagr"].value is None
    assert "undefined" in cl.metrics["eps_cagr"].basis


def test_sector_medians_need_enough_peers():
    pes = [("A", 10.0), ("A", 20.0), ("A", 30.0), ("B", 5.0), ("A", None)]
    assert sector_medians(pes, 3) == {"A": (20.0, 3)}


def test_symbol_mapping():
    assert eodhd.symbol("KPG") == "KPG.AU"
    assert eodhd.symbol("KPG.AX") == "KPG.AU"
    assert eodhd.symbol("ASX:KPG") == "KPG.AU"
    with pytest.raises(eodhd.EODHDNotCovered):
        eodhd.symbol("D05.SI")
