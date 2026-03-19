# 🎯 100-Bagger: Autonomous Multibagger Stock Screening Agent

> The hunt for 100-Bagger stocks or Bigfoot... both are hard to find!!

An autonomous stock-screening agent targeting **ASX** (Australia) and **SGX** (Singapore) that identifies potential multibagger stocks using empirically-validated criteria from the most rigorous academic study ever conducted on ten-bagger returns.

## Research Foundation

This system is built on three complementary sources:

1. **Anna Yartseva (2025)** — *"The Alchemy of Multibagger Stocks"* (CAFÉ Working Paper No. 33, Birmingham City University). Econometric analysis of 464 U.S. stocks achieving 10x+ returns, 2009–2024. Identifies **statistically causal** factors, not just correlations.

2. **Alta Fox Capital (2020)** — Qualitative study of 104 stocks with >350% TSR across North America, Europe, and Australia.

3. **Multibagger Ideas SQGLP Framework** — Small size, Quality returns, Growth potential, Longevity of moats, Price.

## What the Data Actually Says

| ✅ What Predicts Returns | ❌ What Doesn't |
|---|---|
| Free cash flow yield (FCF/P) — **#1 predictor** | Historical earnings growth (any form) |
| Book-to-market ratio (B/M > 0.40) | P/E ratio (distortive, useless) |
| Small company size (< $250M sweet spot) | Debt levels (among winners) |
| ROA and EBITDA margin (specific profitability) | R&D spending |
| Investment discipline (asset growth ≤ EBITDA growth) | 3-6 month momentum (actually negative) |
| Price near 12-month lows | Dividend yield |
| Favourable interest rate environment | Analyst coverage |

## Architecture

```
Universe Builder → Hard Filters → Scoring Engine → Ranking → Report Generator
      ↕                ↕              ↕              ↕            ↕
                    DATA LAYER (Yahoo Finance, FMP API, ASX/SGX Feeds)
```

The agent runs monthly, screens ~1,500 ASX+SGX stocks through a multi-phase pipeline, and generates Goldman Sachs-quality research reports on the top 30 candidates.

## Quick Start

```bash
# Clone the repo
git clone https://github.com/JohnnyM77/100-Bagger.git
cd 100-Bagger

# Install dependencies
pip install -r requirements.txt

# Configure API keys
cp config/data_sources.example.yaml config/data_sources.yaml
# Edit with your FMP API key

# Run the full screening pipeline
python scripts/run_full_screen.py --exchange ASX
python scripts/run_full_screen.py --exchange SGX
```

## Project Structure

```
100-bagger/
├── config/                    # Screening rules, API config, exchange settings
│   └── screening_rules.yaml   # The complete empirically-derived screening criteria
├── src/
│   ├── screener/              # Universe building, filtering, scoring, ranking
│   └── reports/               # Report generation with Jinja2 templates
├── docs/
│   └── BLUEPRINT.md           # Complete technical blueprint (start here)
├── scripts/                   # Runnable pipeline scripts
├── reports/                   # Generated candidate reports (output)
└── tests/                     # Unit and integration tests
```

## Documentation

📄 **[Full Technical Blueprint](docs/BLUEPRINT.md)** — The complete specification including:
- Extracted multibagger criteria synthesis (all three research sources)
- Codeable screening rules in YAML with exact thresholds
- Agent architecture with recommended tech stack
- Company report template at Goldman Sachs quality

## Key Design Decisions

**Why FCF Yield over P/E?** The P/E ratio showed zero predictive power across every model specification. It was actively distortive. FCF yield captures real cash generation and market undervaluation simultaneously.

**Why near 52-week lows?** The Overreaction Hypothesis is confirmed by the data. Stocks near 12-month highs underperform; those beaten down (especially by 30%+ over 6 months) deliver the strongest forward returns. Buy fear, not euphoria.

**Why exclude earnings growth from screening?** This is the most counterintuitive finding. Every form of historical earnings growth tested — EPS, revenue, operating profit, net income, FCF growth, YoY, 5-year CAGR — was statistically insignificant. The *source and quality* of growth matters far more than the growth number itself.

**Why ASX + SGX?** The Alta Fox study found that Australia was *over-represented* among high-TSR stocks relative to its share of the investable universe. Singapore provides APAC exposure with strong IFRS-aligned accounting standards.

## Roadmap

- [x] Research synthesis and criteria extraction
- [x] Technical blueprint and architecture design
- [x] Screening rules specification (YAML)
- [x] Report template specification
- [ ] Core screening engine implementation
- [ ] Data fetcher with caching and rate limiting
- [ ] Report generator with Jinja2 templates
- [ ] LLM qualitative overlay (Claude API integration)
- [ ] Historical backtest on ASX 2015-2024
- [ ] GitHub Actions automated monthly screening
- [ ] Dashboard / notification system
- [ ] HKEX, LSE, TSX exchange modules

## Disclaimer

This is a research and educational tool. It does not constitute investment advice, financial advice, or a recommendation to buy or sell any security. The screening criteria are derived from academic research and may not predict future returns. Always conduct your own due diligence.

## Credits

- **Anna Yartseva** — *"The Alchemy of Multibagger Stocks"*, CAFÉ Working Paper No. 33, Centre for Applied Finance and Economics, Birmingham City University, February 2025. Published under Creative Commons BY-NC-SA license.
- **Alta Fox Capital Management** — *"The Makings of a Multibagger"*, 2020 Summer Intern Class Project.
- **Multibagger Ideas** (Nico) — SQGLP framework and three-part series interpreting the Yartseva research.

## License

MIT
