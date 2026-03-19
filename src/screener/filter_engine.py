import logging

logger = logging.getLogger(__name__)


class FilterEngine:
    def __init__(self, rules: dict = None):
        self.rules = rules or {}

    def apply_all_filters(self, ticker: str, data: dict) -> tuple:
        """
        Runs all hard filters. Returns (passed: bool, filter_results: dict).
        filter_results maps filter name to pass/fail for report transparency.
        """
        results = {}

        checks = [
            ("fcf_positive",          self._filter_fcf_positive(data)),
            ("book_to_market",        self._filter_book_to_market(data)),
            ("roa_positive",          self._filter_roa_positive(data)),
            ("ebitda_positive",       self._filter_ebitda_positive(data)),
            ("investment_discipline", self._filter_investment_discipline(data)),
            ("not_near_52w_high",     self._filter_not_near_52w_high(data)),
            ("sufficient_history",    self._filter_sufficient_history(data)),
        ]

        for name, passed in checks:
            results[name] = passed

        all_passed = all(results.values())

        if not all_passed:
            failed = [k for k, v in results.items() if not v]
            logger.debug(f"{ticker} failed filters: {failed}")

        return all_passed, results

    def _filter_fcf_positive(self, data: dict) -> bool:
        """FCF yield must be positive — #1 predictor per Yartseva (2025)."""
        return data.get("fcf_yield", 0) > 0

    def _filter_book_to_market(self, data: dict) -> bool:
        """Book-to-market ratio must be >= 0.40 (i.e., P/B <= 2.5)."""
        return data.get("book_to_market", 0) >= 0.40

    def _filter_roa_positive(self, data: dict) -> bool:
        """Return on Assets must be positive."""
        return data.get("roa", 0) > 0

    def _filter_ebitda_positive(self, data: dict) -> bool:
        """EBITDA must be positive (operating profitability check)."""
        return data.get("ebitda_ttm", 0) > 0

    def _filter_investment_discipline(self, data: dict) -> bool:
        """
        Asset growth must not significantly exceed EBITDA growth.
        Flags companies over-investing relative to earnings power.
        """
        asset_growth = data.get("asset_growth", 0)
        ebitda_growth = data.get("ebitda_growth", 0)
        if asset_growth <= 0:
            return True
        if ebitda_growth >= 0 and asset_growth <= ebitda_growth * 1.5:
            return True
        if asset_growth < 0.20:
            return True
        return False

    def _filter_not_near_52w_high(self, data: dict) -> bool:
        """
        Avoid stocks within 5% of their 52-week high.
        Overreaction Hypothesis: beaten-down stocks outperform.
        """
        current = data.get("current_price", 0)
        high = data.get("price_52w_high", 0)
        if not high or not current:
            return True
        return (current / high) < 0.95

    def _filter_sufficient_history(self, data: dict) -> bool:
        """Must have at least 2 years of financial data."""
        return data.get("years_of_data", 0) >= 2
