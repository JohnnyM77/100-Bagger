# The 100-Bagger Autonomous Screening Agent — Technical Blueprint

**Version 1.0 | March 2026**
**Targeting: ASX (Australia) & SGX (Singapore)**

> Based on Anna Yartseva's working paper *"The Alchemy of Multibagger Stocks"* (CAFÉ Working Paper No. 33, Birmingham City University, Feb 2025), the Multibagger Ideas SQGLP framework, and the Alta Fox Capital 2020 intern study of 104 high-TSR stocks.

---

## Table of Contents

1. [Extracted Multibagger Criteria Summary](#1-extracted-multibagger-criteria-summary)
2. [Codeable Screening Rules](#2-codeable-screening-rules)
3. [Agent Architecture Blueprint](#3-agent-architecture-blueprint)
4. [Report Template — Company Analysis Specification](#4-report-template)

---

## 1. Extracted Multibagger Criteria Summary

### 1.1 Research Foundation

The framework synthesises three complementary sources:

**Source A — Yartseva (2025):** Econometric analysis of 464 U.S.-listed stocks achieving 10x+ returns between 2009–2024. Used dynamic panel models, fixed effects, GMM estimators, and out-of-sample validation on 2023–2024 data. The study identifies *statistically causal* factors, not merely correlations. This is the most rigorous academic study on multibagger characteristics ever published.

**Source B — Alta Fox Capital (2020):** Qualitative and quantitative analysis of 104 stocks with >350% TSR from June 2015 to June 2020. Covers North America, Western Europe, and Australia. Identifies patterns in moats, management, acquisitions, and industry dynamics.

**Source C — Multibagger Ideas SQGLP Framework:** A practical investing framework (Small size, Quality returns, Growth potential, Longevity of moats, Price) that maps directly onto the Yartseva findings.

### 1.2 Statistically Significant Positive Factors (What Drives Returns)

#### Factor 1: Free Cash Flow Yield (FCF/P) — THE #1 PREDICTOR

- The single most powerful predictor across *every* model specification
- A 1% increase in FCF-to-price ratio correlated with **7–52% higher future returns** depending on model
- Coefficients were the highest in absolute terms across every model; strongly statistically significant with positive sign
- This captures two things simultaneously: (a) the company generates real, disposable cash, and (b) the market has not yet priced it in
- **Practical implication:** Screen for companies generating significant free cash flow relative to their share price — NOT companies with the flashiest revenue growth or earnings beats

#### Factor 2: Book-to-Market Ratio (B/M) — THE VALUE SIGNAL

- The second most predictive variable across the study; the most consistent factor — it held across every size group, profitability level, and investment pattern
- **Threshold: B/M > 0.40** — combined with positive profitability, this places a company into the portfolio group with the highest probability of positive excess returns
- Together with FCF yield, tells a consistent story: multibagger returns are maximised when you buy genuine cash-generating businesses at cheap prices
- P/E ratio was explicitly rejected in favour of B/M and FCF yield as superior valuation measures

#### Factor 3: Small Company Size (Logged TEV)

- Strongly negative coefficient (i.e., smaller = better) across every model specification
- Companies below **$250M market cap** delivered **37.7% annual excess returns** — nearly 4x what large caps delivered (9.7%)
- The low base effect in action: small companies have more room to grow, attract less institutional attention, and are more likely to be mispriced
- **Note for ASX/SGX adaptation:** Many ASX/SGX companies are inherently smaller; the relative size threshold should be calibrated to exchange-specific distributions

#### Factor 4: Profitability — ROA and EBITDA Margin Specifically

- ROA and EBITDA margin both showed significance at different stages of the analysis
- **Key threshold:** Positive operating profitability combined with high B/M value placed stocks in the best-performing portfolios
- Companies with **negative profitability were consistently the worst performers**
- **Critical nuance:** Standard operating profitability metrics (like gross margin alone) showed near-zero predictive power. The specific metrics that matter are ROA (return on assets) and EBITDA margin — these capture how efficiently the business converts its asset base into cash earnings
- ROE was insignificant in the dynamic models; the answer is specifically free cash flow yield and ROA

#### Factor 5: Aggressive Investment Supported by EBITDA Growth

- Ten-baggers were investing heavily — growing their asset base aggressively
- **BUT that investment had to be affordable**: The moment asset growth exceeded EBITDA growth, future returns dropped by **4–11 percentage points**
- The winners were companies expanding aggressively *while* growing earnings to fund it
- This is a disciplined capital allocation signal, not a raw growth signal

#### Factor 6: Entry Price Near 12-Month Lows

- The entry point matters enormously
- Stocks trading near their 12-month highs tend to underperform the following year (**strongly negative** and statistically significant across multiple models)
- Stocks near their 12-month lows — especially those that have fallen significantly over the preceding 6 months — deliver the best forward returns
- This is the **Overreaction Hypothesis** in action: stocks that have run up significantly tend to be overbought; the market has already priced in the good news and often overshot
- **Practical implication:** The best time to buy a future ten-bagger isn't when it's hitting new highs — it's when it's been beaten down

#### Factor 7: Favourable Interest Rate Environment (Contextual Modifier)

- When rates are rising, multibagger stock returns above the risk-free rate drop by approximately **8–12 percentage points** the following year
- However, even during rate hikes, the multibagger portfolio still outperformed the market — returns were just lower
- This is a *timing/sizing* variable, not a screening variable: increase position sizes when rates are stable or declining

### 1.3 Statistically Insignificant Factors to DEPRIORITISE

These variables were tested extensively and found to have **zero or near-zero predictive power** for differentiating returns *among* multibagger stocks. **Do not use these as primary screening criteria:**

| Factor | Status | Why |
|--------|--------|-----|
| **Historical earnings growth** (EPS, revenue, gross profit, operating profit, net income, FCF growth — YoY, 5yr cumulative, 5yr CAGR) | **ALL insignificant** | Past growth does not reliably predict *future* stock returns. Pattern-matching on a lagging indicator. |
| **P/E ratio** | **Zero predictive power; distortive** | Excluded entirely from final models. Replaced by B/M and FCF yield. Negative earnings make it uninterpretable; small earnings inflate it to infinity. |
| **Debt levels** | **Insignificant among winners** | Does not differentiate bigger winners from smaller ones. However, see survivorship caveat below. |
| **R&D spending** | **Insignificant among winners** | Same survivorship caveat. |
| **Capital allocation decisions** | **Insignificant among winners** | Survivorship bias — bad allocators never made it into the dataset. |
| **Dividend yield** | **Insignificant** | Not a differentiator among ten-baggers. |
| **3–6 month momentum** | **NEGATIVE coefficients** | Stocks rising over 3–6 months were *more* likely to decline the following year. Trend reversal, not continuation. |
| **Analyst coverage** | **Insignificant** | — |

### 1.4 Exclusion / Red Flag Criteria

**The "Anti-Multibagger" Profile — Automatic Screen-Out:**

Small-cap stocks that are simultaneously:
- **Overvalued** (low B/M, low FCF yield)
- **Unprofitable** (negative ROA, negative EBITDA)
- **Shrinking assets** (negative asset growth)

→ This combination lost **18.1% annually** in the study. Hard reject.

### 1.5 The Qualitative Gap — What the Model Cannot See

Yartseva explicitly acknowledges that her quantitative models cannot capture certain factors that are critical for real-world investment success. These require human or AI-assisted qualitative overlay:

1. **Competitive Moats** — Switching costs, network effects, barriers to entry, cost advantages, intangible assets. The study measures the *output* of moats (profitability) but not the *input* (the moat itself). A high ROA today means nothing if a competitor can replicate the business model tomorrow.

2. **Management Quality** — Are they aligned with shareholders? Do they have a track record of intelligent reinvestment? Are they competent, honest, and incentivised correctly? The study can measure EBITDA margins but not whether the person making decisions is worth backing.

3. **Capital Allocation Discipline** — Found statistically insignificant due to survivorship bias (companies that destroyed capital never achieved 10x). In practice, a CEO who dilutes shareholders, overpays for acquisitions, or burns cash on vanity projects will never become a ten-bagger. This must be assessed qualitatively.

4. **The Narrative / Catalyst** — A stock can screen perfectly on every quantitative metric and sit there for years. What the model can't capture is *why now* — the business inflection, new product cycle, regulatory tailwind, or management change that unlocks value. This is where real research lives.

5. **Industry Structure & Secular Trends** — The Alta Fox study found that 91% of 350%+ returners had moderate-to-high competitive advantages and 80% had moderate-to-high barriers to entry. Technology and healthcare were over-represented. These structural factors are qualitative.

### 1.6 Cross-Referencing with Alta Fox Study (Validation & Supplements)

The Alta Fox study of 104 stocks with >350% TSR from 2015–2020 provides qualitative validation:

| Alta Fox Finding | Yartseva Alignment |
|---|---|
| 84% of outperformers were below $2B market cap | ✅ Size effect confirmed — smaller is better |
| EBITDA growth contributed ~60% of TSR (avg) | ✅ EBITDA margin/growth is significant predictor |
| Multiple expansion contributed ~45% of TSR (avg) | ✅ B/M (value) captures re-rating potential |
| 56% of companies used acquisitions as key growth lever | ✅ Asset growth is positive — when supported by EBITDA |
| 91% had moderate-to-high competitive advantages | ⚠️ Qualitative gap — model can't see moats directly |
| 88% came from a position of financial health | ✅ Profitability (ROA/EBITDA) confirmed |
| Many were micro/nano-caps with no analyst coverage | ✅ Small size + mispricing confirmed |
| Australia, UK, Sweden, Germany *over-represented* vs US | ✅ Supports applying framework to ASX/SGX |

### 1.7 ASX/SGX Adaptation Notes

The original research was U.S.-only (NYSE/NASDAQ). Key considerations for ASX and SGX:

- **Threshold calibration:** $250M USD market cap threshold should be converted to AUD/SGD and may need adjustment based on local market cap distributions. ASX micro-caps are structurally smaller.
- **Accounting standards:** Australia uses IFRS (like the Yartseva data); Singapore also uses IFRS-converged standards. B/M ratios should be broadly comparable.
- **FCF calculation:** Verify that operating cash flow and capex are reported consistently. Some SGX-listed companies use different reporting conventions for lease capitalisation.
- **Sector mix:** ASX is heavily weighted toward mining/resources and financials. The study excluded energy, materials, and financials. SGX has significant REITs, shipping, and commodities representation. Apply sector filters accordingly.
- **Liquidity:** Both exchanges have meaningful liquidity constraints for micro-caps. Add minimum average daily value traded filter (recommend AUD/SGD $50K+).
- **Currency:** All financial ratios should be computed in local currency. Cross-listing adjustments needed for dual-listed stocks.

---

## 2. Codeable Screening Rules

### 2.1 Screening Rules in YAML Schema

```yaml
# 100-Bagger Multibagger Screening Configuration
# Based on Yartseva (2025), Alta Fox (2020), SQGLP Framework

metadata:
  version: "1.0"
  exchanges: ["ASX", "SGX"]
  base_currency_asx: "AUD"
  base_currency_sgx: "SGD"
  rebalance_frequency: "monthly"
  research_paper: "Yartseva, The Alchemy of Multibagger Stocks, CAFÉ WP No.33, 2025"

# ============================================================
# PHASE 1: UNIVERSE DEFINITION
# ============================================================
universe:
  exchanges:
    - code: "ASX"
      min_daily_value_traded: 50000  # AUD
    - code: "SGX"
      min_daily_value_traded: 50000  # SGD
  
  excluded_sectors:
    # Per Yartseva methodology and Alta Fox methodology
    - "Energy"
    - "Materials"       # Includes mining — major for ASX
    - "Financials"      # Includes banks, REITs
    - "Utilities"
  
  min_listing_age_days: 365      # Avoid recent IPOs with limited data
  must_be_primary_listing: true  # Exclude secondary listings
  actively_trading: true

# ============================================================
# PHASE 2: HARD FILTERS (Binary pass/fail)
# ============================================================
hard_filters:

  # --- SIZE: Small is better ---
  market_cap:
    max_usd: 2000000000    # $2B USD hard ceiling (Alta Fox: 84% below $2B)
    preferred_max_usd: 250000000  # $250M USD sweet spot (Yartseva: 37.7% annual excess)
    note: "Convert to local currency at screening time"

  # --- EXCLUSION: Anti-Multibagger Profile ---
  # Reject if ALL THREE are true simultaneously
  anti_multibagger_reject:
    condition: "ALL_OF"
    rules:
      - book_to_market: "< 0.40"
      - roa_ttm: "< 0"
      - asset_growth_yoy: "< 0"
    action: "HARD_REJECT"
    reason: "Overvalued + unprofitable + shrinking = -18.1% annual loss profile"

# ============================================================
# PHASE 3: SCORING CRITERIA (Weighted composite score)
# ============================================================
scoring:

  # --- FACTOR 1: Free Cash Flow Yield (THE #1 PREDICTOR) ---
  fcf_yield:
    formula: "free_cash_flow_ttm / market_cap"
    weight: 0.30            # Highest weight — most powerful predictor
    scoring:
      - range: ">= 0.10"
        score: 100           # 10%+ FCF yield — exceptional
      - range: ">= 0.06"
        score: 80
      - range: ">= 0.03"
        score: 60
      - range: ">= 0.01"
        score: 40
      - range: ">= 0.00"
        score: 20
      - range: "< 0.00"
        score: 0             # Negative FCF — weakest
    data_source: "operating_cash_flow - capex (from cash flow statement)"
    proxy_if_missing: "EBITDA - capex (less reliable)"

  # --- FACTOR 2: Book-to-Market Value ---
  book_to_market:
    formula: "total_shareholders_equity / market_cap"
    weight: 0.20
    scoring:
      - range: ">= 1.00"
        score: 100           # Deep value
      - range: ">= 0.60"
        score: 80
      - range: ">= 0.40"
        score: 60            # Threshold from research
      - range: ">= 0.20"
        score: 40
      - range: "< 0.20"
        score: 20
    note: "B/M > 0.40 combined with positive profitability = highest probability portfolio"

  # --- FACTOR 3: Size (Smaller = Better) ---
  size_score:
    formula: "log(enterprise_value)"
    weight: 0.15
    scoring:
      - range: "market_cap < 50M USD"
        score: 100           # Nano-cap
        label: "nano_cap"
      - range: "market_cap < 250M USD"
        score: 85            # Micro-cap sweet spot
        label: "micro_cap"
      - range: "market_cap < 500M USD"
        score: 65
        label: "small_cap"
      - range: "market_cap < 1B USD"
        score: 45
        label: "small_mid"
      - range: "market_cap < 2B USD"
        score: 25
        label: "mid_cap"

  # --- FACTOR 4: Profitability (ROA & EBITDA Margin) ---
  profitability:
    weight: 0.15
    sub_factors:
      roa:
        formula: "net_income_ttm / total_assets"
        sub_weight: 0.50
        scoring:
          - range: ">= 0.15"
            score: 100
          - range: ">= 0.08"
            score: 75
          - range: ">= 0.03"
            score: 50
          - range: ">= 0.00"
            score: 25
          - range: "< 0.00"
            score: 0
      ebitda_margin:
        formula: "ebitda_ttm / revenue_ttm"
        sub_weight: 0.50
        scoring:
          - range: ">= 0.25"
            score: 100
          - range: ">= 0.15"
            score: 75
          - range: ">= 0.08"
            score: 50
          - range: ">= 0.00"
            score: 25
          - range: "< 0.00"
            score: 0

  # --- FACTOR 5: Investment Discipline ---
  investment_discipline:
    weight: 0.10
    formula: "asset_growth_rate <= ebitda_growth_rate"
    scoring:
      # Best: growing assets AND EBITDA growing faster
      - condition: "asset_growth > 0 AND ebitda_growth > asset_growth"
        score: 100
        label: "disciplined_growth"
      # Good: growing assets, EBITDA keeping pace
      - condition: "asset_growth > 0 AND ebitda_growth >= 0 AND ebitda_growth >= asset_growth * 0.8"
        score: 70
        label: "moderate_discipline"
      # Caution: assets growing faster than EBITDA
      - condition: "asset_growth > ebitda_growth AND ebitda_growth >= 0"
        score: 30
        label: "undisciplined_growth"
      # Red flag: assets growing, EBITDA shrinking
      - condition: "asset_growth > 0 AND ebitda_growth < 0"
        score: 0
        label: "value_destruction"

  # --- FACTOR 6: Price Position (Near 12-Month Low) ---
  price_position:
    weight: 0.10
    formula: "(current_price - low_52w) / (high_52w - low_52w)"
    note: "0% = at 12-month low, 100% = at 12-month high"
    scoring:
      - range: "<= 0.15"
        score: 100           # Near 12-month low — best entry
      - range: "<= 0.30"
        score: 80
      - range: "<= 0.50"
        score: 50
      - range: "<= 0.75"
        score: 25
      - range: "> 0.75"
        score: 0             # Near 12-month high — strong negative predictor

# ============================================================
# PHASE 4: COMPOSITE SCORING & RANKING
# ============================================================
ranking:
  composite_formula: "sum(factor_score * factor_weight) for all factors"
  min_composite_score: 50    # Minimum to qualify for report generation
  max_candidates_per_run: 30 # Top N candidates sent to report generation
  tiebreaker: "fcf_yield"    # If tied, prefer higher FCF yield

# ============================================================
# PHASE 5: CONTEXTUAL OVERLAYS (Non-scoring modifiers)
# ============================================================
contextual:
  interest_rate_environment:
    source: "RBA cash rate for ASX, MAS rates for SGX"
    modifier:
      rising: "flag_caution"      # Expect 8-12pp headwind; reduce position sizing
      stable_or_falling: "flag_favourable"
    note: "Does not change screening — affects position sizing recommendation in report"

  recent_6m_drawdown:
    formula: "(current_price - price_6m_ago) / price_6m_ago"
    threshold: "<= -0.30"
    action: "flag_contrarian_opportunity"
    note: "30%+ decline in 6 months — premium entry per Overreaction Hypothesis"
```

### 2.2 Data Source Mapping (ASX + SGX)

```yaml
data_sources:
  primary:
    - name: "Yahoo Finance API (yfinance)"
      coverage: "ASX (.AX suffix), SGX (.SI suffix)"
      provides: ["price", "market_cap", "52w_high", "52w_low", "volume"]
      rate_limit: "2000 requests/hour"
      cost: "Free"
      reliability: "Good for price data; financial statements may lag"
    
    - name: "Financial Modelling Prep (FMP) API"
      coverage: "ASX and SGX via global endpoints"
      provides: ["income_statement", "balance_sheet", "cash_flow", "ratios", "enterprise_value"]
      rate_limit: "250-750/day depending on plan"
      cost: "$29-79/month"
      reliability: "Good; IFRS-normalised financials"
    
    - name: "Polygon.io"
      coverage: "ASX limited; SGX limited. Better for US."
      provides: ["price", "financials"]
      note: "Backup source — coverage gaps for APAC"

  secondary:
    - name: "ASX Company Announcements API"
      url: "https://www.asx.com.au/asx/statistics/announcements.do"
      provides: ["company announcements", "disclosure documents"]
      note: "For catalyst detection; scraping required"

    - name: "SGX Company Disclosures"
      url: "https://www.sgx.com/securities/company-announcements"
      provides: ["financial results", "material announcements"]
      note: "For catalyst detection; scraping required"

    - name: "Simply Wall St API / Data"
      provides: ["snowflake scores", "valuation models", "ownership data"]
      cost: "Paid"
      note: "Useful for qualitative overlay data — insider ownership, analyst coverage count"

  enrichment:
    - name: "OpenFIGI"
      provides: ["FIGI identifiers for cross-referencing"]
    - name: "Exchange Rate APIs"
      provides: ["AUD/USD, SGD/USD for market cap normalisation"]

  hard_to_automate:
    - criterion: "Competitive moat assessment"
      proxy: "Sustained high ROA over 5+ years as indirect moat signal"
      manual_fallback: "LLM analysis of annual report MD&A section"
    
    - criterion: "Management quality"
      proxy: "Insider ownership %, track record of capital allocation (M&A history)"
      manual_fallback: "LLM analysis of earnings call transcripts"
    
    - criterion: "Catalyst / narrative"
      proxy: "Recent material announcements, new contract wins, regulatory changes"
      manual_fallback: "LLM web search + news analysis"
```

---

## 3. Agent Architecture Blueprint

### 3.1 System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    100-BAGGER SCREENING AGENT                       │
│                                                                     │
│  ┌───────────┐   ┌───────────┐   ┌────────────┐   ┌─────────────┐ │
│  │ UNIVERSE  │──▶│ SCREENING │──▶│  SCORING   │──▶│   REPORT    │ │
│  │ BUILDER   │   │  ENGINE   │   │  & RANKING │   │ GENERATOR   │ │
│  └───────────┘   └───────────┘   └────────────┘   └─────────────┘ │
│       │               │               │                  │         │
│       ▼               ▼               ▼                  ▼         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                     DATA LAYER                              │   │
│  │  Yahoo Finance │ FMP API │ ASX/SGX Feeds │ Exchange Rates  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│       │                                                            │
│       ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                   STORAGE LAYER                             │   │
│  │  SQLite/PostgreSQL │ JSON Cache │ Report Archive            │   │
│  └─────────────────────────────────────────────────────────────┘   │
│       │                                                            │
│       ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                  OUTPUT / NOTIFICATION                       │   │
│  │  Markdown Reports │ Email Alerts │ Dashboard │ GitHub Push  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 Recommended Tech Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Language** | Python 3.11+ | Richest data science / finance ecosystem |
| **Data fetching** | `yfinance`, `requests`, `httpx` (async) | Free tier for price data; async for parallelism |
| **Financial data API** | Financial Modelling Prep (FMP) | Best APAC coverage for fundamentals at reasonable cost |
| **Data storage** | SQLite (v1) → PostgreSQL (v2) | Start simple; migrate when multi-user or cloud |
| **Caching** | `diskcache` or Redis | Respect API rate limits; avoid redundant calls |
| **Scheduling** | `schedule` library or `cron` | Monthly full screen; weekly price-position check |
| **Report generation** | Jinja2 templates → Markdown → optional DOCX/PDF | Professional output; version-controllable |
| **LLM integration** | Anthropic Claude API (for qualitative overlay) | Analyse annual reports, news, management quality |
| **Orchestration** | Python `asyncio` + task queue | Parallel data fetching; sequential scoring |
| **CI/CD** | GitHub Actions | Automated runs; push reports to repo |
| **Notifications** | Email (SMTP) or Telegram bot | Alert when new candidates pass screening |

### 3.3 Module Breakdown

```
100-bagger/
├── config/
│   ├── screening_rules.yaml       # The YAML schema from Section 2
│   ├── data_sources.yaml          # API keys, endpoints, rate limits
│   └── exchanges.yaml             # ASX/SGX specific settings
├── src/
│   ├── screener/
│   │   ├── universe.py            # Build tradeable universe per exchange
│   │   ├── data_fetcher.py        # Async data retrieval with caching + rate limiting
│   │   ├── hard_filters.py        # Phase 2: Binary pass/fail filters
│   │   ├── scoring_engine.py      # Phase 3: Weighted composite scoring
│   │   ├── ranking.py             # Phase 4: Rank and select top N
│   │   └── contextual.py          # Phase 5: Interest rates, drawdown flags
│   ├── reports/
│   │   ├── report_generator.py    # Orchestrates full report creation
│   │   ├── templates/
│   │   │   └── company_report.md.j2  # Jinja2 template
│   │   ├── qualitative.py         # LLM-powered qualitative overlay
│   │   └── exporter.py            # Markdown → DOCX/PDF conversion
│   ├── data/
│   │   ├── models.py              # SQLAlchemy / dataclass models
│   │   ├── cache.py               # Caching layer
│   │   └── fx_rates.py            # Currency conversion
│   └── utils/
│       ├── logging.py
│       └── rate_limiter.py
├── tests/
│   ├── test_scoring.py
│   ├── test_filters.py
│   └── test_data_fetcher.py
├── scripts/
│   ├── run_full_screen.py         # Monthly full screening pipeline
│   ├── run_price_check.py         # Weekly price-position update
│   └── backtest.py                # Validate screening rules against historical data
├── reports/                       # Generated reports stored here
│   ├── 2026-03/
│   │   ├── ASX_screening_results.md
│   │   ├── SGX_screening_results.md
│   │   └── candidates/
│   │       ├── ASX_XYZ_report.md
│   │       └── SGX_ABC_report.md
├── docs/
│   └── BLUEPRINT.md               # This document
├── requirements.txt
├── pyproject.toml
└── README.md
```

### 3.4 Screening Pipeline Flow

```
TRIGGER: Monthly cron (1st business day) or manual invocation
│
├─ STEP 1: Universe Build
│   ├─ Fetch all active tickers from ASX + SGX
│   ├─ Apply sector exclusions (Energy, Materials, Financials, Utilities)
│   ├─ Apply minimum liquidity filter ($50K avg daily value traded)
│   ├─ Apply minimum listing age (365 days)
│   └─ Output: ~800-1200 ASX candidates, ~300-500 SGX candidates
│
├─ STEP 2: Data Retrieval (Async, Cached)
│   ├─ For each ticker, fetch:
│   │   ├─ Price data (current, 52w high/low, 6m ago price)
│   │   ├─ Market cap, enterprise value
│   │   ├─ Income statement (revenue, EBITDA, net income — TTM)
│   │   ├─ Balance sheet (total assets, total equity, book value)
│   │   ├─ Cash flow statement (operating CF, capex → FCF)
│   │   └─ Prior year comparables (for growth calculations)
│   ├─ Handle missing data: flag, use available proxy, or exclude
│   ├─ Cache all responses (24h TTL for financials, 1h for prices)
│   └─ Log API usage; pause at rate limits
│
├─ STEP 3: Hard Filters
│   ├─ Market cap <= $2B USD equivalent → PASS / FAIL
│   ├─ Anti-multibagger check (overvalued + unprofitable + shrinking) → REJECT if all true
│   └─ Output: Filtered universe (~400-800 companies)
│
├─ STEP 4: Scoring Engine
│   ├─ Calculate all six factor scores per company
│   ├─ Apply weights from config
│   ├─ Compute composite score
│   └─ Output: All companies with composite scores
│
├─ STEP 5: Ranking & Selection
│   ├─ Rank by composite score (descending)
│   ├─ Apply minimum score threshold (50)
│   ├─ Select top 30 candidates
│   └─ Apply contextual flags (interest rate, 6m drawdown)
│
├─ STEP 6: Report Generation (For each candidate)
│   ├─ Gather additional data (if not cached)
│   ├─ Run LLM qualitative overlay (if API key configured)
│   ├─ Populate Jinja2 report template
│   └─ Export to Markdown (and optionally DOCX/PDF)
│
└─ STEP 7: Output & Notification
    ├─ Save reports to /reports/YYYY-MM/
    ├─ Generate screening summary
    ├─ Push to GitHub repository
    └─ Send notification (email/Telegram) with top candidates
```

### 3.5 Data Freshness & Error Handling

| Scenario | Handling |
|----------|----------|
| **API rate limit hit** | Exponential backoff with jitter; queue remaining requests |
| **Missing financial data** | Flag as `DATA_INCOMPLETE`; score available factors only; note in report |
| **Stale financials** (>6 months old) | Flag as `STALE_DATA`; still screen but note in report |
| **Ticker delisted / suspended** | Exclude from universe; log for review |
| **Currency conversion failure** | Use last known rate with staleness flag |
| **API key expired** | Fail gracefully; send alert; skip that data source |

### 3.6 Adding New Exchanges (Modular Design)

To add a new exchange (e.g., HKEX, LSE, TSX):

1. Add exchange entry to `config/exchanges.yaml` with ticker suffix, currency, sector mappings
2. Implement exchange-specific universe builder (sector taxonomy differs per exchange)
3. Add currency pair to FX conversion module
4. Validate that B/M ratio and FCF calculations are compatible with local accounting standards
5. Calibrate size thresholds to local market cap distribution
6. Run backtest against historical data for the new exchange

---

## 4. Report Template

### 4.1 Report Structure Specification

Each automated company report follows this exact structure. The tone and depth should match a Goldman Sachs or Morgan Stanley initiating coverage note — precise, data-grounded, analytically rigorous.

---

### COMPANY REPORT: [TICKER] — [COMPANY NAME]

**Exchange:** [ASX/SGX] | **Sector:** [Sector] | **Market Cap:** [Amount] | **Screening Date:** [Date]
**Composite Score:** [XX/100] | **Rank:** [#X of Y candidates]

---

#### 1. EXECUTIVE SUMMARY

*3–5 sentences. Goldman Sachs initiating-coverage style. State the core thesis, the key metric that makes this company interesting, and the one thing an investor needs to understand.*

> **Example placeholder:** "[Company Name] is a [brief description] trading at [X.X]x FCF yield with a book-to-market ratio of [X.XX], placing it firmly in the empirically-identified sweet spot for multibagger returns. The company has grown EBITDA at [XX]% CAGR while maintaining capital discipline — asset growth has remained below earnings growth for [X] consecutive years. Currently trading [XX]% below its 52-week high following [brief catalyst/reason], the stock presents a contrarian entry point supported by [key qualitative factor]. We flag this for deeper due diligence with [HIGH/MEDIUM] conviction."

---

#### 2. BUSINESS OVERVIEW

- **What the company does:** One paragraph describing the core business, revenue model, and value proposition
- **Market position:** Industry, estimated market share, competitive standing
- **Revenue model:** Recurring vs. one-time; B2B vs. B2C; geographic mix
- **Key customers/segments:** Concentration risk assessment; top customer exposure
- **Employees:** Headcount and trajectory (proxy for operational scaling)

*Data sources: Annual report, company website, FMP API business description*

---

#### 3. MULTIBAGGER FIT ASSESSMENT

Scored breakdown against each Yartseva criterion with real financial data:

| Factor | Metric | Value | Score | Weight | Weighted |
|--------|--------|-------|-------|--------|----------|
| **FCF Yield** | FCF / Market Cap | X.X% | XX/100 | 0.30 | XX |
| **Book-to-Market** | Equity / Market Cap | X.XX | XX/100 | 0.20 | XX |
| **Size** | Market Cap (USD) | $XXM | XX/100 | 0.15 | XX |
| **Profitability** | ROA / EBITDA Margin | X.X% / X.X% | XX/100 | 0.15 | XX |
| **Investment Discipline** | Asset Growth vs EBITDA Growth | XX% vs XX% | XX/100 | 0.10 | XX |
| **Price Position** | % of 52-Week Range | XX% | XX/100 | 0.10 | XX |
| **COMPOSITE** | | | | | **XX/100** |

**Contextual Flags:**
- Interest rate environment: [Rising/Stable/Falling] → [Impact note]
- 6-month drawdown: [XX]% → [Contrarian opportunity flag if applicable]

---

#### 4. FINANCIAL ANALYSIS

**Valuation:**
- FCF Yield: [X.X]% (TTM FCF of [Amount] on market cap of [Amount])
- Book-to-Market: [X.XX] (Book value [Amount], market cap [Amount])
- EV/EBITDA: [X.X]x (for context only — not a primary screening metric)

**Profitability Trajectory:**
- ROA: [Current]% vs [1Y Ago]% vs [3Y Ago]% — trend: [Improving/Stable/Declining]
- EBITDA Margin: [Current]% vs [1Y Ago]% vs [3Y Ago]% — trend: [Improving/Stable/Declining]

**Investment Discipline:**
- Asset growth (YoY): [XX]%
- EBITDA growth (YoY): [XX]%
- Assessment: [Assets growing within EBITDA capacity / Assets outpacing EBITDA — red flag]

**Balance Sheet:**
- Net debt / EBITDA: [X.X]x
- Current ratio: [X.X]
- Note: Debt levels did not differentiate returns in the study, but excessive leverage remains a practical risk

**Forward Estimates (if available):**
- Consensus revenue estimate: [Amount]
- Consensus EPS estimate: [Amount]
- Note: Forward estimates are supplementary context, not screening inputs

---

#### 5. QUALITATIVE ASSESSMENT ⚠️ REQUIRES JUDGMENT

*This section explicitly flags that it addresses factors the quantitative model cannot capture. If LLM-generated, state so clearly.*

**Competitive Moat Analysis:**
- Barriers to entry: [Assessment — HIGH/MEDIUM/LOW with evidence]
- Switching costs: [Assessment]
- Network effects: [Assessment]
- Cost advantages: [Assessment]
- Intangible assets (brand, patents, regulatory licenses): [Assessment]
- Overall moat durability: [Assessment]
- Source: [Annual report / LLM analysis / Manual research — state which]

**Management Quality Indicators:**
- Insider ownership: [XX]%
- Track record of capital allocation: [Assessment based on M&A history, buybacks, dividends]
- Alignment with shareholders: [Assessment]
- Tenure and background: [Brief]

**Capital Allocation Discipline:**
- Historical M&A track record: [Accretive / Dilutive / Mixed]
- Use of excess cash: [Reinvestment / Dividends / Buybacks / Cash hoarding]
- Share dilution history: [Assessment]

---

#### 6. KEY RISKS

*Specific, researched risks. No generic boilerplate.*

1. **[Risk 1 — Named and specific]:** [2-3 sentence description of the risk and its potential impact]
2. **[Risk 2]:** [Description]
3. **[Risk 3]:** [Description]
4. **[Risk 4 — Data quality risk if applicable]:** [Note any data gaps, stale financials, or proxy calculations used]

---

#### 7. VERDICT

**Recommendation:** [WARRANTS DEEPER DUE DILIGENCE / MONITOR / PASS]
**Confidence Level:** [HIGH / MEDIUM / LOW]

**Rationale:** [2-3 sentences explaining the verdict, referencing the strongest supporting factor and the biggest risk]

**What would change our view:**
- Bullish catalyst: [Specific event that would strengthen the thesis]
- Bearish catalyst: [Specific event that would invalidate the thesis]

**Data completeness:** [COMPLETE / PARTIAL — list any missing data points]

---

*Report generated by 100-Bagger Screening Agent v1.0 on [Date]. Based on Yartseva (2025) multibagger criteria. This is a screening output, not investment advice. All qualitative assessments flagged as [LLM-generated / Manual] where applicable.*

---

## Appendix A: Glossary of Key Metrics

| Metric | Formula | Source |
|--------|---------|--------|
| FCF Yield | (Operating Cash Flow - CapEx) / Market Cap | Cash Flow Statement |
| Book-to-Market | Total Shareholders' Equity / Market Cap | Balance Sheet + Price |
| ROA | Net Income (TTM) / Total Assets | Income Statement + Balance Sheet |
| EBITDA Margin | EBITDA (TTM) / Revenue (TTM) | Income Statement |
| Asset Growth | (Total Assets_t - Total Assets_t-1) / Total Assets_t-1 | Balance Sheet |
| EBITDA Growth | (EBITDA_t - EBITDA_t-1) / EBITDA_t-1 | Income Statement |
| Price Position | (Price - 52W Low) / (52W High - 52W Low) | Price Data |

## Appendix B: Backtest Validation Plan

Before deploying to live screening:

1. **Historical ASX backtest (2015–2024):** Screen ASX stocks annually using the criteria; measure hypothetical portfolio returns vs ASX200
2. **Historical SGX backtest (2015–2024):** Same for SGX vs STI
3. **Out-of-sample validation:** Reserve 2023–2024 data; train on 2015–2022
4. **Threshold sensitivity:** Test B/M threshold at 0.30, 0.40, 0.50; test market cap at $100M, $250M, $500M
5. **Sector robustness:** Verify that the model works after excluding mining/financials (critical for ASX)

---

*End of Blueprint v1.0*
