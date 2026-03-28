"""
main.py — Orchestrator for the 100-Bagger stock scanner.

Usage:
    python -m scanner.main                        # ASX + SGX, full run
    python -m scanner.main --exchange asx         # ASX only
    python -m scanner.main --exchange sgx         # SGX only
    python -m scanner.main --dry-run              # first 50 tickers only
    python -m scanner.main --no-enrich            # skip fundamental enrichment
"""

import argparse
import logging
import os
import smtplib
import time
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .bulk_fetch import fetch_price_stats
from .enricher import enrich
from .report_builder import build_report
from .screener import screen
from .universe import get_universe

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DRY_RUN_LIMIT = 50


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="100-Bagger stock scanner for ASX and SGX."
    )
    parser.add_argument(
        "--exchange",
        choices=["asx", "sgx", "all"],
        default="all",
        help="Exchange(s) to scan (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=f"Process only the first {DRY_RUN_LIMIT} tickers (for testing)",
    )
    parser.add_argument(
        "--no-enrich",
        action="store_true",
        help="Skip fundamental enrichment and score tickers on price data only",
    )
    parser.add_argument(
        "--force-refresh",
        action="store_true",
        help="Bypass the universe cache and re-fetch from source",
    )
    return parser.parse_args()


def _send_email(md_body: str, metadata: dict) -> None:
    """Send the markdown report as an HTML email using SMTP env vars."""
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_password = os.environ.get("SMTP_PASSWORD", "")
    email_from = os.environ.get("EMAIL_FROM", smtp_user)
    email_to = os.environ.get("EMAIL_TO", "")

    if not all([smtp_host, smtp_user, smtp_password, email_to]):
        logger.info("Email not configured — skipping (set SMTP_HOST, SMTP_USER, SMTP_PASSWORD, EMAIL_TO)")
        return

    run_date = metadata["date"]
    candidates = metadata["candidates_found"]
    scanned = metadata["total_scanned"]
    subject = f"100-Bagger Scan — {run_date} ({candidates} candidates from {scanned:,} tickers)"

    # Wrap markdown in a minimal HTML shell so it renders readably in email clients
    html = (
        "<html><body style='font-family:monospace;white-space:pre-wrap;"
        "font-size:13px;color:#222;max-width:900px;margin:0 auto;padding:24px'>"
        + md_body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        + "</body></html>"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_from
    msg["To"] = email_to
    msg.attach(MIMEText(md_body, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(email_from, email_to, msg.as_string())
        print(f"  Email sent to {email_to}")
    except Exception as exc:
        logger.error("Failed to send email: %s", exc)


def main() -> None:
    """Run the full scan pipeline."""
    args = parse_args()
    start_time = time.time()
    run_date = date.today().isoformat()

    exchanges = (
        ["ASX", "SGX"] if args.exchange == "all" else [args.exchange.upper()]
    )

    print(f"\n{'='*60}")
    print(f"  100-Bagger Scanner — {run_date}")
    print(f"  Exchanges : {', '.join(exchanges)}")
    if args.dry_run:
        print(f"  Mode      : DRY RUN (first {DRY_RUN_LIMIT} tickers only)")
    if args.no_enrich:
        print("  Enrichment: DISABLED")
    print(f"{'='*60}\n")

    # -----------------------------------------------------------------------
    # Step 1: Universe
    # -----------------------------------------------------------------------
    print("Step 1/5 — Loading universe...")
    universe = get_universe(exchanges=exchanges, force_refresh=args.force_refresh)

    if not universe:
        logger.error("Universe is empty — check network access and data sources.")
        raise SystemExit(1)

    print(f"  Universe loaded: {len(universe):,} tickers\n")

    tickers = [e.ticker for e in universe]
    if args.dry_run:
        tickers = tickers[:DRY_RUN_LIMIT]
        universe = [e for e in universe if e.ticker in set(tickers)]
        print(f"  Dry-run: trimmed to {len(tickers)} tickers\n")

    # -----------------------------------------------------------------------
    # Step 2: Bulk price fetch
    # -----------------------------------------------------------------------
    print(f"Step 2/5 — Fetching 1-year prices for {len(tickers):,} tickers...")
    price_data = fetch_price_stats(tickers)
    print(f"  Price data: {len(price_data):,} tickers with sufficient history\n")

    # -----------------------------------------------------------------------
    # Step 3: Screen
    # -----------------------------------------------------------------------
    print("Step 3/5 — Applying filters...")
    candidates = screen(universe, price_data)
    print(
        f"  Screening complete. {len(candidates)} candidates from "
        f"{len(price_data):,} tickers.\n"
    )

    if not candidates:
        logger.warning("No candidates passed any filter — check thresholds.")

    # -----------------------------------------------------------------------
    # Step 4: Enrich
    # -----------------------------------------------------------------------
    fundamentals: dict = {}
    if not args.no_enrich and candidates:
        print(f"Step 4/5 — Enriching {len(candidates)} candidates with fundamentals...")
        fundamentals = enrich(candidates)
        print(f"  Enrichment complete: {len(fundamentals)} tickers enriched.\n")
    else:
        print("Step 4/5 — Skipping enrichment (--no-enrich or no candidates).\n")

    # -----------------------------------------------------------------------
    # Step 5: Report
    # -----------------------------------------------------------------------
    print("Step 5/5 — Building report...")
    runtime_s = time.time() - start_time
    metadata = {
        "date": run_date,
        "exchanges": exchanges,
        "total_scanned": len(tickers),
        "tickers_with_price_data": len(price_data),
        "candidates_found": len(candidates),
        "runtime_seconds": round(runtime_s, 1),
        "dry_run": args.dry_run,
        "enriched": not args.no_enrich,
    }

    json_path, md_path = build_report(candidates, fundamentals, metadata)

    print(f"\n{'='*60}")
    print("  Scan complete!")
    print(f"  JSON : {json_path}")
    print(f"  MD   : {md_path}")
    print(f"  Time : {runtime_s:.0f}s")
    print(f"{'='*60}\n")

    _send_email(md_path.read_text(), metadata)


if __name__ == "__main__":
    main()
