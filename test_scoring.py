"""Tests for the scoring engine — validates Yartseva (2025) criteria implementation."""
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.screener.scoring_engine import ScoringEngine, CompanyData


@pytest.fixture
def engine():
    return ScoringEngine()


@pytest.fixture
def ideal_multibagger():
    """A company that hits every multibagger criterion perfectly."""
    return CompanyData(
        ticker="IDEAL.AX",
        exchange="ASX",
        company_name="Ideal Multibagger Co",
        current_price=1.50,
        high_52w=4.00,
        low_52w=1.20,
        price_6m_ago=3.50,
        market_cap=80_000_000,
        market_cap_usd=52_000_000,
        enterprise_value=75_000_000,
        revenue=40_000_000,
        ebitda=12_000_000,
        net_income=8_000_000,
        total_assets=60_000_000,
        total_equity=45_000_000,
        total_assets_prior=50_000_000,
        operating_cash_flow=15_000_000,
        capex=-3_000_000,
        ebitda_prior=8_000_000,
    )


@pytest.fixture
def anti_multibagger():
    """
    The anti-multibagger profile: overvalued + unprofitable + shrinking.
    Yartseva found this profile lost 18.1% annually.
    """
    return CompanyData(
        ticker="AVOID.AX",
        exchange="ASX",
        company_name="Avoid This Co",
        current_price=0.50,
        high_52w=2.00,
        low_52w=0.30,
        market_cap=500_000_000,
        market_cap_usd=325_000_000,
        enterprise_value=600_000_000,
        revenue=20_000_000,
        ebitda=-5_000_000,
        net_income=-10_000_000,
        total_assets=100_000_000,
        total_equity=30_000_000,       # B/M = 30M/500M = 0.06 < 0.40
        total_assets_prior=120_000_000, # Shrinking assets
        operating_cash_flow=-8_000_000,
        capex=-2_000_000,
        ebitda_prior=-3_000_000,
    )


@pytest.fixture
def mediocre_company():
    """A mid-range company that should score in the 40-60 range."""
    return CompanyData(
        ticker="MEH.SI",
        exchange="SGX",
        company_name="Mediocre Holdings",
        current_price=2.00,
        high_52w=3.00,
        low_52w=1.50,
        price_6m_ago=2.50,
        market_cap=400_000_000,
        market_cap_usd=300_000_000,
        enterprise_value=450_000_000,
        revenue=200_000_000,
        ebitda=20_000_000,
        net_income=10_000_000,
        total_assets=300_000_000,
        total_equity=120_000_000,       # B/M = 0.30
        total_assets_prior=280_000_000,
        operating_cash_flow=15_000_000,
        capex=-10_000_000,
        ebitda_prior=18_000_000,
    )


# ═══════════════════════════════════════════════════════════════
# CORE SCORING TESTS
# ═══════════════════════════════════════════════════════════════

class TestCompositeScoring:

    def test_ideal_multibagger_scores_high(self, engine, ideal_multibagger):
        result = engine.score_company(ideal_multibagger)
        assert result.composite_score >= 70, (
            f"Ideal multibagger should score >= 70, got {result.composite_score:.1f}"
        )

    def test_anti_multibagger_scores_low(self, engine, anti_multibagger):
        result = engine.score_company(anti_multibagger)
        assert result.composite_score < 40, (
            f"Anti-multibagger should score < 40, got {result.composite_score:.1f}"
        )

    def test_mediocre_company_scores_mid_range(self, engine, mediocre_company):
        result = engine.score_company(mediocre_company)
        assert 25 <= result.composite_score <= 65, (
            f"Mediocre company should score 25-65, got {result.composite_score:.1f}"
        )

    def test_composite_bounded_0_to_100(self, engine, ideal_multibagger):
        result = engine.score_company(ideal_multibagger)
        assert 0 <= result.composite_score <= 100

    def test_weights_sum_to_one(self, engine):
        total = sum(engine.WEIGHTS.values())
        assert total == pytest.approx(1.0), f"Weights must sum to 1.0, got {total}"


# ═══════════════════════════════════════════════════════════════
# FACTOR 1: FCF YIELD — THE #1 PREDICTOR
# ═══════════════════════════════════════════════════════════════

class TestFCFYield:

    def test_high_fcf_yield_scores_100(self, engine, ideal_multibagger):
        result = engine.score_company(ideal_multibagger)
        # FCF = 15M - 3M = 12M, Market Cap = 80M → FCF Yield = 15%
        assert result.fcf_yield == pytest.approx(0.15, abs=0.01)
        assert result.fcf_yield_score == 100

    def test_negative_fcf_scores_zero(self, engine):
        data = CompanyData(
            ticker="BURN.AX", exchange="ASX", company_name="Cash Burner",
            current_price=2, high_52w=5, low_52w=1,
            market_cap=100_000_000, market_cap_usd=65_000_000,
            operating_cash_flow=-5_000_000, capex=-2_000_000,
        )
        result = engine.score_company(data)
        assert result.fcf_yield < 0
        assert result.fcf_yield_score == 0

    def test_fcf_yield_has_highest_weight(self, engine):
        assert engine.WEIGHTS["fcf_yield"] == 0.30
        assert engine.WEIGHTS["fcf_yield"] == max(engine.WEIGHTS.values())


# ═══════════════════════════════════════════════════════════════
# FACTOR 2: BOOK-TO-MARKET — THE VALUE SIGNAL
# ═══════════════════════════════════════════════════════════════

class TestBookToMarket:

    def test_bm_above_040_threshold(self, engine, ideal_multibagger):
        result = engine.score_company(ideal_multibagger)
        # B/M = 45M / 80M = 0.5625 > 0.40 threshold
        assert result.book_to_market > 0.40
        assert result.book_to_market_score >= 60

    def test_deep_value_scores_highest(self, engine):
        data = CompanyData(
            ticker="DEEP.AX", exchange="ASX", company_name="Deep Value Co",
            current_price=0.50, high_52w=2.00, low_52w=0.40,
            market_cap=20_000_000, market_cap_usd=13_000_000,
            total_equity=25_000_000,  # B/M = 1.25
        )
        result = engine.score_company(data)
        assert result.book_to_market >= 1.0
        assert result.book_to_market_score == 100


# ═══════════════════════════════════════════════════════════════
# FACTOR 3: SIZE — SMALLER IS BETTER
# ═══════════════════════════════════════════════════════════════

class TestSize:

    def test_microcap_scores_very_high(self, engine, ideal_multibagger):
        result = engine.score_company(ideal_multibagger)
        # $52M USD = micro-cap (above $50M nano threshold, below $250M)
        assert result.size_score == 85

    def test_larger_cap_scores_lower(self, engine):
        data = CompanyData(
            ticker="BIG.AX", exchange="ASX", company_name="Big Co",
            current_price=10, high_52w=15, low_52w=8,
            market_cap=1_500_000_000, market_cap_usd=1_500_000_000,
        )
        result = engine.score_company(data)
        assert result.size_score <= 45


# ═══════════════════════════════════════════════════════════════
# FACTOR 5: INVESTMENT DISCIPLINE
# ═══════════════════════════════════════════════════════════════

class TestInvestmentDiscipline:

    def test_ebitda_growing_faster_than_assets_scores_100(self, engine, ideal_multibagger):
        result = engine.score_company(ideal_multibagger)
        # Asset growth = (60-50)/50 = 20%, EBITDA growth = (12-8)/8 = 50%
        assert result.asset_growth == pytest.approx(0.20, abs=0.01)
        assert result.ebitda_growth == pytest.approx(0.50, abs=0.01)
        assert result.investment_discipline_score == 100

    def test_assets_outpacing_ebitda_penalised(self, engine):
        """When asset growth exceeds EBITDA growth, returns drop 4-11pp."""
        data = CompanyData(
            ticker="SPEND.AX", exchange="ASX", company_name="Overspender",
            current_price=3, high_52w=5, low_52w=2,
            market_cap=100_000_000, market_cap_usd=65_000_000,
            total_assets=200_000_000, total_assets_prior=100_000_000,  # 100% asset growth
            ebitda=15_000_000, ebitda_prior=12_000_000,  # 25% EBITDA growth
            revenue=50_000_000,
        )
        result = engine.score_company(data)
        assert result.investment_discipline_score <= 30

    def test_growing_assets_shrinking_ebitda_scores_zero(self, engine):
        data = CompanyData(
            ticker="DESTROY.AX", exchange="ASX", company_name="Value Destroyer",
            current_price=1, high_52w=3, low_52w=0.80,
            market_cap=50_000_000, market_cap_usd=33_000_000,
            total_assets=100_000_000, total_assets_prior=80_000_000,  # Growing
            ebitda=5_000_000, ebitda_prior=10_000_000,  # Shrinking
            revenue=40_000_000,
        )
        result = engine.score_company(data)
        assert result.investment_discipline_score <= 30


# ═══════════════════════════════════════════════════════════════
# FACTOR 6: PRICE POSITION — NEAR 12-MONTH LOWS
# ═══════════════════════════════════════════════════════════════

class TestPricePosition:

    def test_near_52w_low_scores_highest(self, engine, ideal_multibagger):
        result = engine.score_company(ideal_multibagger)
        # Position = (1.50 - 1.20) / (4.00 - 1.20) = 0.107 → near low
        assert result.price_position_pct < 0.15
        assert result.price_position_score == 100

    def test_near_52w_high_scores_zero(self, engine):
        """Stocks near 12-month highs = strong negative predictor."""
        data = CompanyData(
            ticker="HOT.AX", exchange="ASX", company_name="Momentum Stock",
            current_price=9.80, high_52w=10.00, low_52w=3.00,
            market_cap=100_000_000, market_cap_usd=65_000_000,
        )
        result = engine.score_company(data)
        assert result.price_position_pct > 0.90
        assert result.price_position_score == 0


# ═══════════════════════════════════════════════════════════════
# ANTI-MULTIBAGGER DETECTION
# ═══════════════════════════════════════════════════════════════

class TestAntiMultibagger:

    def test_detects_anti_multibagger(self, engine, anti_multibagger):
        result = engine.score_company(anti_multibagger)
        assert result.is_anti_multibagger is True

    def test_ideal_is_not_anti_multibagger(self, engine, ideal_multibagger):
        result = engine.score_company(ideal_multibagger)
        assert result.is_anti_multibagger is False

    def test_only_two_of_three_not_flagged(self, engine):
        """Anti-multibagger requires ALL THREE: overvalued + unprofitable + shrinking."""
        # Overvalued + unprofitable but NOT shrinking
        data = CompanyData(
            ticker="PARTIAL.AX", exchange="ASX", company_name="Partial Match",
            current_price=5, high_52w=8, low_52w=3,
            market_cap=500_000_000, market_cap_usd=325_000_000,
            total_equity=30_000_000,         # B/M = 0.06 < 0.40 ✓ overvalued
            net_income=-5_000_000,           # ✓ unprofitable
            total_assets=100_000_000,
            total_assets_prior=90_000_000,   # ✗ GROWING, not shrinking
        )
        result = engine.score_company(data)
        assert result.is_anti_multibagger is False


# ═══════════════════════════════════════════════════════════════
# CONTRARIAN OPPORTUNITY FLAG
# ═══════════════════════════════════════════════════════════════

class TestContrarianFlag:

    def test_30pct_drawdown_flagged(self, engine, ideal_multibagger):
        result = engine.score_company(ideal_multibagger)
        # Price: 3.50 → 1.50 = -57% drawdown
        assert result.is_contrarian_opportunity is True
        assert result.drawdown_6m < -0.30

    def test_small_drawdown_not_flagged(self, engine, mediocre_company):
        result = engine.score_company(mediocre_company)
        # Price: 2.50 → 2.00 = -20% drawdown
        assert result.is_contrarian_opportunity is False


# ═══════════════════════════════════════════════════════════════
# EDGE CASES
# ═══════════════════════════════════════════════════════════════

class TestEdgeCases:

    def test_zero_market_cap(self, engine):
        data = CompanyData(
            ticker="ZERO.AX", exchange="ASX", company_name="Zero Cap",
            current_price=0, high_52w=1, low_52w=0,
            market_cap=0, market_cap_usd=0,
        )
        result = engine.score_company(data)
        assert result.fcf_yield == 0.0
        assert result.book_to_market == 0.0

    def test_zero_revenue(self, engine):
        data = CompanyData(
            ticker="PREREV.AX", exchange="ASX", company_name="Pre-Revenue",
            current_price=0.50, high_52w=1, low_52w=0.30,
            market_cap=10_000_000, market_cap_usd=6_500_000,
            revenue=0, ebitda=-1_000_000,
        )
        result = engine.score_company(data)
        assert result.ebitda_margin == 0.0

    def test_flat_52w_range(self, engine):
        """Stock that hasn't moved — 52w high == low."""
        data = CompanyData(
            ticker="FLAT.AX", exchange="ASX", company_name="Flatline",
            current_price=5.00, high_52w=5.00, low_52w=5.00,
            market_cap=50_000_000, market_cap_usd=33_000_000,
        )
        result = engine.score_company(data)
        assert result.price_position_pct == 0.5  # Default when range is zero

    def test_no_prior_year_data(self, engine):
        data = CompanyData(
            ticker="NEW.SI", exchange="SGX", company_name="New Listing",
            current_price=1.00, high_52w=1.50, low_52w=0.80,
            market_cap=30_000_000, market_cap_usd=22_000_000,
            total_assets=20_000_000, total_assets_prior=0,  # No prior year
            ebitda=2_000_000, ebitda_prior=0,
        )
        result = engine.score_company(data)
        assert result.asset_growth == 0.0  # Graceful handling
