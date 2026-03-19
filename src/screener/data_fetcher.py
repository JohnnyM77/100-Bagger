import os
import time
import pickle
import logging
import requests
from pathlib import Path
from datetime import datetime, date, timedelta

logger = logging.getLogger(__name__)


class DataFetcher:
    def __init__(self, api_key: str, cache_dir: str = ".cache"):
        self.api_key = api_key
        self.base_url = "https://financialmodelingprep.com/api/v3"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.month_key = datetime.now().strftime("%Y-%m")

    def _cache_path(self, ticker: str, endpoint: str) -> Path:
        safe_ticker = ticker.replace("/", "_").replace(".", "_")
        return self.cache_dir / f"{safe_ticker}_{endpoint}_{self.month_key}.pkl"

    def _get(self, endpoint: str, ticker: str = "", params: dict = None) -> dict | list:
        cache_key = endpoint.replace("/", "_").strip("_")
        cache_file = self._cache_path(ticker, cache_key)

        if cache_file.exists():
            try:
                with open(cache_file, "rb") as f:
                    return pickle.load(f)
            except Exception:
                pass

        url = f"{self.base_url}/{endpoint}"
        all_params = {"apikey": self.api_key}
        if params:
            all_params.update(params)

        try:
            time.sleep(0.25)
            resp = requests.get(url, params=all_params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            with open(cache_file, "wb") as f:
                pickle.dump(data, f)
            return data
        except Exception as e:
            logger.warning(f"FMP API error for {ticker}/{endpoint}: {e}")
            return {} if any(k in endpoint for k in ["profile", "ratios", "metrics"]) else []

    def get_exchange_tickers(self, exchange: str) -> list:
        data = self._get("stock-screener", exchange, {
            "exchange": exchange,
            "limit": 3000
        })
        if isinstance(data, list):
            return [item.get("symbol", "") for item in data if item.get("symbol")]
        return []

    def get_company_profile(self, ticker: str) -> dict:
        data = self._get(f"profile/{ticker}", ticker)
        if isinstance(data, list) and data:
            return data[0]
        return {}

    def get_financial_ratios(self, ticker: str) -> dict:
        data = self._get(f"ratios-ttm/{ticker}", ticker)
        if isinstance(data, list) and data:
            return data[0]
        return {}

    def get_income_statement(self, ticker: str, limit: int = 5) -> list:
        data = self._get(f"income-statement/{ticker}", ticker, {"limit": limit})
        return data if isinstance(data, list) else []

    def get_cash_flow_statement(self, ticker: str, limit: int = 5) -> list:
        data = self._get(f"cash-flow-statement/{ticker}", ticker, {"limit": limit})
        return data if isinstance(data, list) else []

    def get_balance_sheet(self, ticker: str, limit: int = 3) -> list:
        data = self._get(f"balance-sheet-statement/{ticker}", ticker, {"limit": limit})
        return data if isinstance(data, list) else []

    def get_key_metrics(self, ticker: str) -> dict:
        data = self._get(f"key-metrics-ttm/{ticker}", ticker)
        if isinstance(data, list) and data:
            return data[0]
        return {}

    def get_price_history(self, ticker: str, from_date: str, to_date: str) -> list:
        data = self._get(f"historical-price-full/{ticker}", ticker, {
            "from": from_date,
            "to": to_date
        })
        if isinstance(data, dict):
            return data.get("historical", [])
        return []

    def fetch_all(self, ticker: str) -> dict:
        profile = self.get_company_profile(ticker)
        ratios = self.get_financial_ratios(ticker)
        income = self.get_income_statement(ticker)
        cashflow = self.get_cash_flow_statement(ticker)
        balance = self.get_balance_sheet(ticker)

        today = date.today()
        one_year_ago = today - timedelta(days=365)
        prices = self.get_price_history(ticker, one_year_ago.isoformat(), today.isoformat())

        price_52w_high = max((p.get("high", 0) for p in prices), default=0)
        price_52w_low = min((p.get("low", float("inf")) for p in prices), default=0)
        current_price = prices[0].get("close", 0) if prices else 0

        total_assets_current = balance[0].get("totalAssets", 0) if balance else 0
        total_assets_prior = balance[1].get("totalAssets", 0) if len(balance) > 1 else 0
        ebitda_current = income[0].get("ebitda", 0) if income else 0
        ebitda_prior = income[1].get("ebitda", 0) if len(income) > 1 else 0

        asset_growth = (
            (total_assets_current - total_assets_prior) / abs(total_assets_prior)
            if total_assets_prior else 0
        )
        ebitda_growth = (
            (ebitda_current - ebitda_prior) / abs(ebitda_prior)
            if ebitda_prior else 0
        )

        return {
            "ticker": ticker,
            "name": profile.get("companyName", ticker),
            "sector": profile.get("sector", ""),
            "industry": profile.get("industry", ""),
            "description": profile.get("description", ""),
            "country": profile.get("country", ""),
            "exchange": profile.get("exchangeShortName", ""),
            "market_cap": profile.get("mktCap", 0),
            "current_price": current_price,
            "price_52w_high": price_52w_high,
            "price_52w_low": price_52w_low,
            "fcf_yield": ratios.get("freeCashFlowYieldTTM", 0),
            "price_to_book": ratios.get("priceToBookRatioTTM", 0),
            "book_to_market": (
                1 / ratios.get("priceToBookRatioTTM", 1)
                if ratios.get("priceToBookRatioTTM", 0) > 0 else 0
            ),
            "roa": ratios.get("returnOnAssetsTTM", 0),
            "ebitda_margin": ratios.get("ebitdaPerSharaTTM", 0),
            "debt_to_equity": ratios.get("debtEquityRatioTTM", 0),
            "current_ratio": ratios.get("currentRatioTTM", 0),
            "revenue_ttm": income[0].get("revenue", 0) if income else 0,
            "ebitda_ttm": income[0].get("ebitda", 0) if income else 0,
            "free_cash_flow_ttm": cashflow[0].get("freeCashFlow", 0) if cashflow else 0,
            "total_assets": total_assets_current,
            "total_debt": balance[0].get("totalDebt", 0) if balance else 0,
            "asset_growth": asset_growth,
            "ebitda_growth": ebitda_growth,
            "years_of_data": len(income),
        }
