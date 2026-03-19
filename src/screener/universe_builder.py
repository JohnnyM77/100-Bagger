import logging
import pandas as pd
from .data_fetcher import DataFetcher

logger = logging.getLogger(__name__)

EXCLUDED_SECTORS = {"Real Estate", "Financial Services", "Banks", "Insurance"}
EXCLUDED_KEYWORDS = ["REIT", "ETF", "LIC", "Infrastructure", "Listed Investment"]


class UniverseBuilder:
    def __init__(self, data_fetcher: DataFetcher, config: dict):
        self.fetcher = data_fetcher
        self.config = config

    def build_universe(self, exchange: str) -> pd.DataFrame:
        """
        Builds investable universe for the given exchange by:
        1. Fetching all tickers
        2. Applying fast hard filters (market cap, sector, data history)
        3. Returning a DataFrame of candidates for deep scoring
        """
        logger.info(f"Building universe for {exchange}...")
        exc_config = self.config.get("exchanges", {}).get(exchange, {})
        min_cap = exc_config.get("market_cap_min", 10_000_000)
        max_cap = exc_config.get("market_cap_max", 2_000_000_000)

        tickers = self.fetcher.get_exchange_tickers(exchange)
        logger.info(f"  Raw ticker count: {len(tickers)}")

        candidates = []
        for ticker in tickers:
            profile = self.fetcher.get_company_profile(ticker)
            if not profile:
                continue

            market_cap = profile.get("mktCap", 0)
            if not (min_cap <= market_cap <= max_cap):
                continue

            sector = profile.get("sector", "")
            if sector in EXCLUDED_SECTORS:
                continue

            name = profile.get("companyName", "")
            if any(kw.lower() in name.lower() for kw in EXCLUDED_KEYWORDS):
                continue

            income = self.fetcher.get_income_statement(ticker, limit=3)
            if len(income) < 2:
                continue

            candidates.append({
                "ticker": ticker,
                "name": name,
                "market_cap": market_cap,
                "sector": sector,
                "industry": profile.get("industry", ""),
                "exchange": exchange,
            })

        logger.info(f"  Universe after hard filters: {len(candidates)}")
        return pd.DataFrame(candidates)
