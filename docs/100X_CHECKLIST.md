# The 100x checklist, as the bot computes it

Source: *How to hunt for 100-baggers, an investment check-list* (Kevin,
100 Bagger Hunting, Sep 2023), based on Christopher Mayer's *100 Baggers*.
The article's message is **buy right, then hold on**. This bot handles the
"buy right" filter. Holding on is up to you.

Each line is graded **Yikes / Meh / Good / Great** (0 / 1 / 2 / 3 points).
Thresholds are in `config/checklist.yaml`. All inputs come from EODHD. If
EODHD has no figure, the line shows **n/a** and scores nothing (see CLAUDE.md).

| # | Criterion | Yikes | Meh | Good | Great | How the bot gets it (EODHD) |
|---|---|---|---|---|---|---|
| 1 | Sales growth CAGR | <10% | 10–15% | >15% | >25% | `Financials.Income_Statement.yearly.totalRevenue`, CAGR over up to 10 FYs (at least 3) |
| 2 | Gross margin | <20% | 20–50% | >50% | >70% | latest FY `grossProfit / totalRevenue` |
| 3 | EPS growth | <5% | 5–10% | >10% | >20% | EPS = `netIncome / commonStockSharesOutstanding` per FY, CAGR over up to 5 FYs (at least 3); n/a if either end is ≤ 0 |
| 4 | Return on equity | <5% | 5–15% | >15% | >25% | `Highlights.ReturnOnEquityTTM` |
| 5 | Return on invested capital | <5% | 5–15% | >15% | >25% | latest FY `operatingIncome × (1 − reported tax rate)` / average of (`totalStockholderEquity + shortLongTermDebtTotal − cashAndShortTermInvestments`) for the last 2 FYs |
| 6 | Sound capital allocation | No | Sort of | Yes | Holy | **judgement**. Evidence shown: 5-yr share-count change, FCF history |
| 7 | Incentives aligned | None | Sort of | Yes | Holy S& | **judgement**. Evidence shown: `SharesStats.PercentInsiders`, founder among `General.Officers` |
| 8 | Long-term moat | None | Sort of | Yes | Holy S& | **judgement**. Use #2 and #5 as clues |
| 9 | Number of analysts | >10 | 5–10 | <5 | 0 | sum of `AnalystRatings` StrongBuy…StrongSell; `"NA"` = n/a (check manually) |
| 10 | Great work culture | To avoid | OK | Unique | Cult-like | **judgement**. No data |
| 11 | Discount to median PE | <15% | >15% | >30% | >50% | `Valuation.TrailingPE` vs median trailing PE of positive-PE sector peers in the same hunt (min 5 peers) |
| 12 | PEG ratio | >2 | 1–2 | <1 | <0.7 | `Highlights.PEGRatio` (forward). If EODHD has none: trailing PE ÷ EPS CAGR (#3), labelled as trailing |
| 13 | Small market cap (US$bn) | >10 | 5–10 | <5 | <1 | `Highlights.MarketCapitalization` × EODHD `AUDUSD.FOREX` |

## How the search engine works (`python -m scanner.hunt`)

1. **EODHD screener**: every ASX stock with market cap A$20m–A$15bn and
   positive EPS. Energy and Basic Materials are excluded by default, because
   the article warns that resources flood high-ROE screens. Average daily
   value traded must be at least A$20k.
2. **EODHD fundamentals** for each survivor (cached 7 days).
3. **Grade** the 9 quantitative lines. A company needs data on at least 6 of
   them to be ranked. Ranking is by % of available points, so n/a neither
   helps nor hurts.
4. **Report**: top-30 table plus full checklist cards for the top 10, with the
   four judgement lines set out as prompts. Saved as JSON and Markdown in
   `scanner/data/outputs/` and emailed if SMTP is configured.

Use `python -m scanner.hunt --ticker KPG --ticker XYZ` to run the checklist on
any ASX names you already have in mind.

## Caveats (in keeping with the article)

- This is a filter, not a verdict. The article itself says luck is a factor,
  and that quality plus cheapness is rare. Expect the top of the list to need
  real research.
- EODHD's standardised `grossProfit` can differ from a company's own
  definition, especially for services businesses. Check the annual report
  before relying on #2.
- Small ASX companies often have no EODHD analyst or PEG record, so lines 9
  and 12 are frequently n/a. That is reported honestly, not filled in.
