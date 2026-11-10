# CLAUDE.md — rules for anyone (human or AI) working in this repo

## Rule #1: never guess a number. EODHD is the only source of market data.

Every share price, market cap, volume, FX rate, ratio and financial-statement
figure this repo uses or prints **must come from EODHD**, through
`scanner/eodhd.py`. That is the same paid EODHD account, and the same
`EODHD_API_TOKEN` secret, that Bob the Bot and the other agents in
`JohnnyM77/Reporting-Agent` use (`shared/eodhd.py` there).

- **Never guess, estimate, "recall", round-trip from memory, back-solve or
  invent a figure.** Not in code, reports, emails, commit messages, PR text or
  chat answers about this repo's stocks. If you (Claude) are asked for a price,
  P/E, market cap, revenue, EPS, ROE etc., fetch it from EODHD (the EODHD MCP
  tools or `scanner/eodhd.py`) and say it came from EODHD and as of when.
- **If EODHD has no figure, show `n/a` with the reason.** A missing number is
  acceptable; a guessed one is not. No fallback to another source, no
  placeholder values, no "typical" or sector-average stand-ins, no defaulting
  missing data to 0 when 0 would change a score.
- **No second data source.** Do not add yfinance / Yahoo prices, FMP, Alpha
  Vantage, scraped quote pages or hand-typed numbers. `tests/test_eodhd_only.py`
  fails the build if one appears in `scanner/` or its workflow.
- **Label the source and the date.** Reports say "EODHD" and the as-of date
  (EOD trading date, fundamentals `UpdatedAt`, FX date).
- **Derived numbers are fine when they are pure maths on EODHD fields** (CAGR,
  margins, ROIC, PE vs peer median, USD conversion at the EODHD AUDUSD rate),
  and the report says how each was derived. Fixed rule constants (checklist
  thresholds in `config/checklist.yaml`) are configuration, not data.
- **Coverage limits are stated, not papered over.** SGX (Singapore) is not on
  the EODHD plan, so the scanner is ASX-only; `eodhd.symbol()` raises
  `EODHDNotCovered` for `.SI` tickers.

### EODHD conventions

- ASX symbols are `CODE.AU` in EODHD (not Yahoo's `.AX`). `eodhd.symbol("KPG")`
  -> `KPG.AU`; reports display `ASX:KPG`.
- Token env var: `EODHD_API_TOKEN` (`EODHD_API_KEY` also accepted). GitHub
  Actions secret: `EODHD_API_TOKEN`.
- Costs: `/fundamentals` = 10 API calls (cached on disk 7 days in
  `scanner/data/cache/`), `/screener` = 5 per page, `/eod` and `/real-time` = 1.
  The account limit is 100k calls/day and is shared with Bob the Bot, so keep
  the cache on.
- EODHD reports a missing P/E or forward P/E as `0`; treat `<= 0` as n/a.
  `AnalystRatings` is the string `"NA"` when there is no record — that is
  n/a, not "0 analysts".

## What lives where

| Path | What |
|---|---|
| `scanner/eodhd.py` | the only market-data client (stdlib HTTP, retries, disk cache) |
| `scanner/checklist.py` | the 13-point 100x checklist, computed from an EODHD fundamentals record |
| `scanner/hunt.py` | search engine: EODHD screener → fundamentals → checklist → ranked report (`python -m scanner.hunt`, or `--ticker KPG` for one card) |
| `scanner/main.py` + `universe.py`, `bulk_fetch.py`, `screener.py`, `enricher.py`, `report_builder.py` | the older price-pattern scan (MOMENTUM / BREAKOUT / DEEP_VALUE), now on EODHD |
| `config/checklist.yaml` | checklist thresholds and hunt filters — tune here, not in code |
| `docs/100X_CHECKLIST.md` | how each checklist line maps to EODHD fields |
| `src/`, `scripts/run_full_screen.py`, `.github/workflows/monthly_screen.yml` | **legacy** FMP/yfinance pipeline. Not EODHD-compliant; do not use its numbers or extend it |

## Running

```bash
pip install -r scanner/requirements.txt
export EODHD_API_TOKEN=...            # never commit it
python -m scanner.hunt --ticker KPG   # one company's checklist card
python -m scanner.hunt --limit 40     # quick test hunt
python -m scanner.hunt                # full ASX hunt -> scanner/data/outputs/
python -m pytest tests/test_checklist.py tests/test_eodhd_only.py -q
```
