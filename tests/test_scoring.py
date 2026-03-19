import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.screener.scoring_engine import ScoringEngine
from src.screener.filter_engine import FilterEngine


GOOD_STOCK = {
    "ticker": "TEST.AX",
    "name": "Test Company",
    "market_cap": 100_000_000,
    "fcf_yield": 0.08,
    "book_to_market": 0.65,
    "roa": 0.10,
    "revenue_ttm": 50_000_000,
    "ebitda_ttm": 12_000_000,
    "free_cash_flow_ttm": 8_000_000,
    "current_price": 1.20,
    "price_52w_high": 2.00,
    "debt_to_equity": 0.3,
    "asset_growth": 0.05,
    "ebitda_growth": 0.12,
    "years_of_data": 4,
}

BAD_STOCK = {
    "ticker": "BAD.AX",
    "name": "Bad Company",
    "market_cap": 500_000_000,
    "fcf_yield": -0.02,
    "book_to_market": 0.20,
    "roa": -0.05,
    "revenue_ttm": 100_000_000,
    "ebitda_ttm": -1_000_000,
    "free_cash_flow_ttm": -2_000_000,
    "current_price": 4.90,
    "price_52w_high": 5.00,
    "debt_to_equity": 1.5,
    "asset_growth": 0.40,
    "ebitda_growth": 0.05,
    "years_of_data": 1,
}


class TestFilterEngine:
    def setup_method(self):
        self.engine = FilterEngine()

    def test_good_stock_passes_all_filters(self):
        passed, results = self.engine.apply_all_filters("TEST.AX", GOOD_STOCK)
        assert passed, f"Good stock failed filters: {[k for k, v in results.items() if not v]}"

    def test_negative_fcf_fails(self):
        data = {**GOOD_STOCK, "fcf_yield": -0.01}
        passed, results = self.engine.apply_all_filters("TEST.AX", data)
        assert not passed
        assert not results["fcf_positive"]

    def test_high_pb_fails(self):
        data = {**GOOD_STOCK, "book_to_market": 0.30}
        passed, results = self.engine.apply_all_filters("TEST.AX", data)
        assert not passed
        assert not results["book_to_market"]

    def test_near_52w_high_fails(self):
        data = {**GOOD_STOCK, "current_price": 4.97, "price_52w_high": 5.00}
        passed, results = self.engine.apply_all_filters("TEST.AX", data)
        assert not passed
        assert not results["not_near_52w_high"]

    def test_insufficient_history_fails(self):
        data = {**GOOD_STOCK, "years_of_data": 1}
        passed, results = self.engine.apply_all_filters("TEST.AX", data)
        assert not passed
        assert not results["sufficient_history"]

    def test_bad_stock_fails(self):
        passed, _ = self.engine.apply_all_filters("BAD.AX", BAD_STOCK)
        assert not passed


class TestScoringEngine:
    def setup_method(self):
        self.engine = ScoringEngine()

    def test_score_returns_tuple(self):
        score, breakdown = self.engine.score(GOOD_STOCK)
        assert isinstance(score, float)
        assert isinstance(breakdown, dict)

    def test_score_within_range(self):
        score, _ = self.engine.score(GOOD_STOCK)
        assert 0 <= score <= 100

    def test_breakdown_has_all_dimensions(self):
        _, breakdown = self.engine.score(GOOD_STOCK)
        expected = {
            "fcf_yield", "book_to_market", "size", "roa",
            "ebitda_margin", "investment_discipline", "price_dislocation"
        }
        assert expected == set(breakdown.keys())

    def test_higher_fcf_yields_higher_score(self):
        low_fcf = {**GOOD_STOCK, "fcf_yield": 0.02}
        high_fcf = {**GOOD_STOCK, "fcf_yield": 0.12}
        score_low, _ = self.engine.score(low_fcf)
        score_high, _ = self.engine.score(high_fcf)
        assert score_high > score_low

    def test_good_stock_scores_above_50(self):
        score, _ = self.engine.score(GOOD_STOCK)
        assert score > 50, f"Good stock scored only {score}"

    def test_zero_values_do_not_crash(self):
        empty = {k: 0 for k in GOOD_STOCK}
        score, breakdown = self.engine.score(empty)
        assert score == 0.0
