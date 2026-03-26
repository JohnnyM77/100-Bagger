#!/usr/bin/env python3
"""
100-Bagger Full Screening Pipeline

Usage:
    python scripts/run_full_screen.py --exchange ASX
    python scripts/run_full_screen.py --exchange SGX
    python scripts/run_full_screen.py --exchange ALL
"""

import argparse
import logging
import os
import sys
import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.screener.data_fetcher import DataFetcher
from src.screener.universe_builder import UniverseBuilder
from src.screener.filter_engine import FilterEngine
from src.screener.scoring_engine import ScoringEngine
from src.reports.report_generator import ReportGenerator
from src.reports.notifier import EmailNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def load_config() -> dict:
    config = {}
    for path in ["config/screening_rules.yaml", "config/data_sources.yaml"]:
        p = Path(path)
        if p.exists():
            with open(p) as f:
                config.update(yaml.safe_load(f) or {})
    return config


def run_pipeline(exchange: str, config: dict):
    print(f"\n{'='*60}")
    print(f"  Starting 100-Bagger Screen: {exchange}")
    print(f"{'='*60}\n")

    fmp_key = os.environ.get("FMP_API_KEY", "")
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")

    if not fmp_key:
        logger.error("FMP_API_KEY not set. Export it or add to .env file.")
        sys.exit(1)

    fetcher = DataFetcher(api_key=fmp_key)
    builder = UniverseBuilder(fetcher, config)
    filterer = FilterEngine(config.get("screening_rules", {}))
    scorer = ScoringEngine(config.get("scoring_weights", {}))
    reporter = ReportGenerator(
        anthropic_api_key=anthropic_key,
        template_path="src/reports/templates/company_report.md.j2"
    )

    # Stage 1: Build universe
    universe = builder.build_universe(exchange)
    if universe.empty:
        logger.error(
            f"No stocks in universe for {exchange}. "
            f"The FMP API returned no tickers — check your API key is valid and that your "
            f"plan covers the stock-screener or available-traded/list endpoints."
        )
        sys.exit(1)
    print(f"Universe size: {len(universe)} stocks\n")

    # Stage 2: Fetch full data + apply filters
    candidates = []
    total = len(universe)
    for i, row in universe.iterrows():
        ticker = row["ticker"]
        print(f"  Analysing {ticker} ({i+1}/{total})...", end="\r")
        data = fetcher.fetch_all(ticker)
        passed, filter_results = filterer.apply_all_filters(ticker, data)
        if passed:
            data["filter_results"] = filter_results
            candidates.append(data)

    print(f"\nPassed all filters: {len(candidates)} stocks\n")

    if not candidates:
        logger.error(
            "No candidates passed all filters. This usually means the FMP API returned "
            "empty financial data — check your plan covers income-statement and ratios endpoints."
        )
        sys.exit(1)

    # Stage 3: Score and rank
    for c in candidates:
        c["score"], c["score_breakdown"] = scorer.score(c)
    candidates.sort(key=lambda x: x["score"], reverse=True)
    top_n = candidates[:config.get("output", {}).get("top_n_candidates", 30)]
    for rank, c in enumerate(top_n, 1):
        c["rank"] = rank

    print(f"Top {len(top_n)} candidates identified\n")

    # Stage 4: Generate reports
    Path("reports").mkdir(exist_ok=True)
    for c in top_n:
        print(f"  Generating report: {c['ticker']} (#{c['rank']}, score {c['score']:.0f})...")
        reporter.generate_report(c, c["score_breakdown"])

    reporter.generate_summary_table(top_n)
    print(f"\nAll reports saved to reports/\n")

    # Stage 5: Send email notification
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    email_from = os.environ.get("EMAIL_FROM", smtp_user)
    email_to = os.environ.get("EMAIL_TO", "")

    if all([smtp_host, smtp_user, smtp_password, email_to]):
        notifier = EmailNotifier(smtp_host, smtp_port, smtp_user, smtp_password, email_from, email_to)
        notifier.send_summary(top_n, reporter.month_key)
        print(f"Email sent to {email_to}\n")
    else:
        logger.info("Email not configured — skipping (set SMTP_HOST, SMTP_USER, SMTP_PASSWORD, EMAIL_TO in .env)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the 100-Bagger stock screening pipeline.")
    parser.add_argument(
        "--exchange",
        choices=["ASX", "SGX", "ALL"],
        default="ALL",
        help="Which exchange to screen (default: ALL)"
    )
    args = parser.parse_args()
    config = load_config()
    exchanges = ["ASX", "SGX"] if args.exchange == "ALL" else [args.exchange]
    for exchange in exchanges:
        run_pipeline(exchange, config)
