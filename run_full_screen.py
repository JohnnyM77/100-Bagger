#!/usr/bin/env python3
"""
100-Bagger Full Screening Pipeline

Runs the complete multibagger screening process for ASX and/or SGX.

Usage:
    python scripts/run_full_screen.py --exchange ASX
    python scripts/run_full_screen.py --exchange SGX
    python scripts/run_full_screen.py --exchange ALL
    python scripts/run_full_screen.py --exchange ASX --dry-run
"""

import argparse
import sys
import os
import json
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.screener.scoring_engine import ScoringEngine, CompanyData, ScoringResult


def parse_args():
    parser = argparse.ArgumentParser(description="100-Bagger Multibagger Screening Agent")
    parser.add_argument(
        "--exchange",
        choices=["ASX", "SGX", "ALL"],
        default="ALL",
        help="Which exchange(s) to screen",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=30,
        help="Maximum candidates per exchange for report generation",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=50.0,
        help="Minimum composite score to qualify for reporting",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run with sample data instead of live API calls",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for reports (default: reports/YYYY-MM/)",
    )
    return parser.parse_args()


def get_sample_data() -> list[CompanyData]:
    """
    Sample data for dry-run testing.
    Replace with real data fetcher in production.
    """
    return [
        CompanyData(
            ticker="PME.AX",
            exchange="ASX",
            company_name="Pro Medicus Limited",
            current_price=85.00,
            high_52w=120.00,
            low_52w=60.00,
            price_6m_ago=110.00,
            market_cap=8_900_000_000,
            market_cap_usd=5_800_000_000,
            enterprise_value=8_800_000_000,
            revenue=190_000_000,
            ebitda=130_000_000,
            net_income=95_000_000,
            total_assets=250_000_000,
            total_equity=200_000_000,
            total_assets_prior=200_000_000,
            operating_cash_flow=120_000_000,
            capex=-10_000_000,
            ebitda_prior=100_000_000,
            sector="Healthcare",
        ),
        CompanyData(
            ticker="NXT.AX",
            exchange="ASX",
            company_name="NEXTDC Limited",
            current_price=12.50,
            high_52w=18.00,
            low_52w=10.00,
            price_6m_ago=16.00,
            market_cap=6_200_000_000,
            market_cap_usd=4_000_000_000,
            enterprise_value=8_500_000_000,
            revenue=400_000_000,
            ebitda=200_000_000,
            net_income=20_000_000,
            total_assets=5_000_000_000,
            total_equity=2_500_000_000,
            total_assets_prior=3_800_000_000,
            operating_cash_flow=250_000_000,
            capex=-600_000_000,
            ebitda_prior=160_000_000,
            sector="Technology",
        ),
        CompanyData(
            ticker="SYA.AX",
            exchange="ASX",
            company_name="Sayona Mining Limited",
            current_price=0.04,
            high_52w=0.12,
            low_52w=0.03,
            price_6m_ago=0.08,
            market_cap=350_000_000,
            market_cap_usd=228_000_000,
            enterprise_value=400_000_000,
            revenue=80_000_000,
            ebitda=-20_000_000,
            net_income=-50_000_000,
            total_assets=800_000_000,
            total_equity=600_000_000,
            total_assets_prior=900_000_000,
            operating_cash_flow=-30_000_000,
            capex=-10_000_000,
            ebitda_prior=-15_000_000,
            sector="Materials",
        ),
        CompanyData(
            ticker="SAMPLE.AX",
            exchange="ASX",
            company_name="Sample Micro-Cap Co",
            current_price=0.85,
            high_52w=2.50,
            low_52w=0.70,
            price_6m_ago=1.80,
            market_cap=45_000_000,
            market_cap_usd=29_000_000,
            enterprise_value=40_000_000,
            revenue=30_000_000,
            ebitda=6_000_000,
            net_income=3_500_000,
            total_assets=25_000_000,
            total_equity=18_000_000,
            total_assets_prior=22_000_000,
            operating_cash_flow=5_500_000,
            capex=-1_000_000,
            ebitda_prior=4_000_000,
            sector="Technology",
        ),
        CompanyData(
            ticker="SGX_SAMPLE.SI",
            exchange="SGX",
            company_name="Sample SGX Small-Cap",
            current_price=0.45,
            high_52w=0.80,
            low_52w=0.35,
            price_6m_ago=0.70,
            market_cap=120_000_000,
            market_cap_usd=90_000_000,
            enterprise_value=110_000_000,
            revenue=60_000_000,
            ebitda=10_000_000,
            net_income=5_000_000,
            total_assets=80_000_000,
            total_equity=55_000_000,
            total_assets_prior=70_000_000,
            operating_cash_flow=8_000_000,
            capex=-2_000_000,
            ebitda_prior=7_000_000,
            sector="Industrials",
        ),
    ]


def run_screening(
    companies: list[CompanyData],
    exchange_filter: str,
    max_candidates: int,
    min_score: float,
) -> list[ScoringResult]:
    """Run the full screening pipeline on a list of companies."""
    engine = ScoringEngine()

    # Filter by exchange
    if exchange_filter != "ALL":
        companies = [c for c in companies if c.exchange == exchange_filter]

    print(f"\n{'='*60}")
    print(f"  SCREENING: {exchange_filter} | {len(companies)} companies")
    print(f"{'='*60}\n")

    # Score all companies
    results = []
    for company in companies:
        result = engine.score_company(company)
        results.append(result)

    # Filter out anti-multibaggers
    anti_count = sum(1 for r in results if r.is_anti_multibagger)
    results = [r for r in results if not r.is_anti_multibagger]
    print(f"  Anti-multibagger profiles rejected: {anti_count}")

    # Apply minimum score
    results = [r for r in results if r.composite_score >= min_score]
    print(f"  Candidates above {min_score} score threshold: {len(results)}")

    # Sort by composite score (descending), tiebreak on FCF yield
    results.sort(key=lambda r: (r.composite_score, r.fcf_yield), reverse=True)

    # Take top N
    results = results[:max_candidates]
    print(f"  Top candidates selected: {len(results)}")

    return results


def print_results(results: list[ScoringResult]):
    """Print a formatted results table."""
    if not results:
        print("\n  No candidates passed screening.\n")
        return

    print(f"\n  {'Rank':<5} {'Ticker':<15} {'Name':<30} {'Score':>7} {'FCF%':>7} {'B/M':>6} {'Size$':>10} {'PricePos':>9} {'Flags'}")
    print(f"  {'─'*5} {'─'*15} {'─'*30} {'─'*7} {'─'*7} {'─'*6} {'─'*10} {'─'*9} {'─'*15}")

    for i, r in enumerate(results, 1):
        flags = []
        if r.is_contrarian_opportunity:
            flags.append("🔥CONTRARIAN")
        if r.data_completeness != "COMPLETE":
            flags.append("⚠️DATA")

        mcap_str = f"${r.fcf_yield * 0 + 0:.0f}"  # placeholder
        # Simple market cap formatting
        flag_str = " ".join(flags)

        print(
            f"  {i:<5} "
            f"{r.ticker:<15} "
            f"{r.company_name[:29]:<30} "
            f"{r.composite_score:>6.1f} "
            f"{r.fcf_yield*100:>6.1f}% "
            f"{r.book_to_market:>5.2f} "
            f"{'micro' if r.size_score >= 85 else 'small' if r.size_score >= 45 else 'mid':>10} "
            f"{r.price_position_pct*100:>7.1f}% "
            f"{flag_str}"
        )

    print()


def save_results(results: list[ScoringResult], output_dir: Path, exchange: str):
    """Save results as JSON for downstream processing."""
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{exchange}_screening_results.json"

    data = []
    for r in results:
        data.append({
            "ticker": r.ticker,
            "exchange": r.exchange,
            "company_name": r.company_name,
            "composite_score": round(r.composite_score, 2),
            "fcf_yield": round(r.fcf_yield, 4),
            "book_to_market": round(r.book_to_market, 4),
            "roa": round(r.roa, 4),
            "ebitda_margin": round(r.ebitda_margin, 4),
            "asset_growth": round(r.asset_growth, 4),
            "ebitda_growth": round(r.ebitda_growth, 4),
            "price_position_pct": round(r.price_position_pct, 4),
            "is_contrarian_opportunity": r.is_contrarian_opportunity,
            "drawdown_6m": round(r.drawdown_6m, 4),
            "factor_scores": {
                "fcf_yield": r.fcf_yield_score,
                "book_to_market": r.book_to_market_score,
                "size": r.size_score,
                "profitability": r.profitability_score,
                "investment_discipline": r.investment_discipline_score,
                "price_position": r.price_position_score,
            },
        })

    with open(filepath, "w") as f:
        json.dump({"screening_date": datetime.now().isoformat(), "results": data}, f, indent=2)

    print(f"  Results saved to: {filepath}")


def main():
    args = parse_args()
    now = datetime.now()

    print("\n" + "═" * 60)
    print("  100-BAGGER MULTIBAGGER SCREENING AGENT v1.0")
    print(f"  Run Date: {now.strftime('%Y-%m-%d %H:%M')}")
    print(f"  Exchange: {args.exchange}")
    print(f"  Mode: {'DRY RUN (sample data)' if args.dry_run else 'LIVE'}")
    print("═" * 60)

    # Set output directory
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = Path("reports") / now.strftime("%Y-%m")

    # Get data
    if args.dry_run:
        companies = get_sample_data()
        print(f"\n  Loaded {len(companies)} sample companies for dry run")
    else:
        # TODO: Replace with real data fetcher
        print("\n  ⚠️  Live data fetching not yet implemented.")
        print("  Use --dry-run for testing with sample data.")
        print("  See docs/BLUEPRINT.md Section 3 for data source integration plan.\n")
        sys.exit(1)

    # Run screening
    exchanges = ["ASX", "SGX"] if args.exchange == "ALL" else [args.exchange]

    all_results = {}
    for exchange in exchanges:
        results = run_screening(
            companies=companies,
            exchange_filter=exchange,
            max_candidates=args.max_candidates,
            min_score=args.min_score,
        )
        all_results[exchange] = results
        print_results(results)
        if results:
            save_results(results, output_dir, exchange)

    # Summary
    total = sum(len(r) for r in all_results.values())
    print(f"\n{'═'*60}")
    print(f"  SCREENING COMPLETE")
    print(f"  Total candidates across all exchanges: {total}")
    print(f"  Reports directory: {output_dir}")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
