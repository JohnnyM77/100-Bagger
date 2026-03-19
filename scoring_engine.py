"""
Scoring Engine for 100-Bagger Multibagger Screening Agent.

Implements the empirically-derived factor model from Yartseva (2025):
- FCF Yield (weight: 0.30) — #1 predictor
- Book-to-Market (weight: 0.20) — value signal
- Size (weight: 0.15) — smaller is better
- Profitability (weight: 0.15) — ROA + EBITDA margin
- Investment Discipline (weight: 0.10) — asset growth vs EBITDA growth
- Price Position (weight: 0.10) — near 12-month lows preferred
"""

from dataclasses import dataclass, field
from typing import Optional
import math


@dataclass
class CompanyData:
    """Financial data for a single company."""
    ticker: str
    exchange: str
    company_name: str
    
    # Price data
    current_price: float
    high_52w: float
    low_52w: float
    price_6m_ago: Optional[float] = None
    
    # Market data
    market_cap: float = 0.0              # Local currency
    market_cap_usd: float = 0.0          # Converted to USD
    enterprise_value: float = 0.0
    
    # Income statement (TTM)
    revenue: float = 0.0
    ebitda: float = 0.0
    net_income: float = 0.0
    
    # Balance sheet
    total_assets: float = 0.0
    total_equity: float = 0.0            # Shareholders' equity
    total_assets_prior: float = 0.0      # Prior year
    
    # Cash flow (TTM)
    operating_cash_flow: float = 0.0
    capex: float = 0.0                   # Typically negative
    
    # Prior year for growth calcs
    ebitda_prior: float = 0.0
    
    # Metadata
    sector: str = ""
    gics_sector_code: int = 0
    listing_date: str = ""
    data_completeness: str = "COMPLETE"
    missing_fields: list = field(default_factory=list)


@dataclass
class ScoringResult:
    """Complete scoring result for a company."""
    ticker: str
    exchange: str
    company_name: str
    
    # Individual factor scores (0-100)
    fcf_yield_score: float = 0.0
    book_to_market_score: float = 0.0
    size_score: float = 0.0
    profitability_score: float = 0.0
    investment_discipline_score: float = 0.0
    price_position_score: float = 0.0
    
    # Raw metric values
    fcf_yield: float = 0.0
    book_to_market: float = 0.0
    roa: float = 0.0
    ebitda_margin: float = 0.0
    asset_growth: float = 0.0
    ebitda_growth: float = 0.0
    price_position_pct: float = 0.0
    
    # Composite
    composite_score: float = 0.0
    
    # Flags
    is_anti_multibagger: bool = False
    is_contrarian_opportunity: bool = False
    rate_environment: str = "unknown"
    drawdown_6m: float = 0.0
    data_completeness: str = "COMPLETE"
    
    # Weights used
    weights: dict = field(default_factory=lambda: {
        "fcf_yield": 0.30,
        "book_to_market": 0.20,
        "size": 0.15,
        "profitability": 0.15,
        "investment_discipline": 0.10,
        "price_position": 0.10,
    })


class ScoringEngine:
    """
    Multi-factor scoring engine implementing Yartseva (2025) criteria.
    
    Each factor is scored 0-100, then weighted to produce a composite score.
    Higher is better across all factors.
    """
    
    # Factor weights (from Yartseva research priority)
    WEIGHTS = {
        "fcf_yield": 0.30,
        "book_to_market": 0.20,
        "size": 0.15,
        "profitability": 0.15,
        "investment_discipline": 0.10,
        "price_position": 0.10,
    }
    
    def score_company(self, data: CompanyData) -> ScoringResult:
        """Score a single company across all factors."""
        result = ScoringResult(
            ticker=data.ticker,
            exchange=data.exchange,
            company_name=data.company_name,
            data_completeness=data.data_completeness,
        )
        
        # Check anti-multibagger profile first
        result.is_anti_multibagger = self._check_anti_multibagger(data)
        
        # Calculate raw metrics
        result.fcf_yield = self._calc_fcf_yield(data)
        result.book_to_market = self._calc_book_to_market(data)
        result.roa = self._calc_roa(data)
        result.ebitda_margin = self._calc_ebitda_margin(data)
        result.asset_growth = self._calc_asset_growth(data)
        result.ebitda_growth = self._calc_ebitda_growth(data)
        result.price_position_pct = self._calc_price_position(data)
        
        # Score each factor (0-100)
        result.fcf_yield_score = self._score_fcf_yield(result.fcf_yield)
        result.book_to_market_score = self._score_book_to_market(result.book_to_market)
        result.size_score = self._score_size(data.market_cap_usd)
        result.profitability_score = self._score_profitability(result.roa, result.ebitda_margin)
        result.investment_discipline_score = self._score_investment_discipline(
            result.asset_growth, result.ebitda_growth
        )
        result.price_position_score = self._score_price_position(result.price_position_pct)
        
        # Compute composite
        result.composite_score = self._compute_composite(result)
        
        # Contextual flags
        if data.price_6m_ago and data.price_6m_ago > 0:
            result.drawdown_6m = (data.current_price - data.price_6m_ago) / data.price_6m_ago
            result.is_contrarian_opportunity = result.drawdown_6m <= -0.30
        
        return result
    
    # ── Raw Metric Calculations ──────────────────────────────────────
    
    def _calc_fcf_yield(self, d: CompanyData) -> float:
        """FCF/P ratio. The #1 predictor of future multibagger returns."""
        if d.market_cap <= 0:
            return 0.0
        fcf = d.operating_cash_flow - abs(d.capex)
        return fcf / d.market_cap
    
    def _calc_book_to_market(self, d: CompanyData) -> float:
        """Book-to-market ratio. B/M > 0.40 is the key threshold."""
        if d.market_cap <= 0:
            return 0.0
        return d.total_equity / d.market_cap
    
    def _calc_roa(self, d: CompanyData) -> float:
        """Return on assets. Specific profitability metric that matters."""
        if d.total_assets <= 0:
            return 0.0
        return d.net_income / d.total_assets
    
    def _calc_ebitda_margin(self, d: CompanyData) -> float:
        """EBITDA margin. The other profitability metric with significance."""
        if d.revenue <= 0:
            return 0.0
        return d.ebitda / d.revenue
    
    def _calc_asset_growth(self, d: CompanyData) -> float:
        """Year-over-year total asset growth."""
        if d.total_assets_prior <= 0:
            return 0.0
        return (d.total_assets - d.total_assets_prior) / d.total_assets_prior
    
    def _calc_ebitda_growth(self, d: CompanyData) -> float:
        """Year-over-year EBITDA growth."""
        if d.ebitda_prior <= 0 or d.ebitda_prior == 0:
            if d.ebitda > 0:
                return 1.0  # Turned profitable — strong signal
            return 0.0
        return (d.ebitda - d.ebitda_prior) / abs(d.ebitda_prior)
    
    def _calc_price_position(self, d: CompanyData) -> float:
        """
        Where current price sits in the 52-week range.
        0.0 = at 52-week low (best for multibagger entry)
        1.0 = at 52-week high (worst — strong negative predictor)
        """
        range_width = d.high_52w - d.low_52w
        if range_width <= 0:
            return 0.5
        return (d.current_price - d.low_52w) / range_width
    
    # ── Factor Scoring (0-100 scale) ─────────────────────────────────
    
    def _score_fcf_yield(self, fcf_yield: float) -> float:
        """Score FCF yield. Higher FCF yield = higher score."""
        thresholds = [(0.10, 100), (0.06, 80), (0.03, 60), (0.01, 40), (0.00, 20)]
        for threshold, score in thresholds:
            if fcf_yield >= threshold:
                return score
        return 0
    
    def _score_book_to_market(self, bm: float) -> float:
        """Score book-to-market. B/M > 0.40 is key threshold from research."""
        thresholds = [(1.00, 100), (0.60, 80), (0.40, 60), (0.20, 40)]
        for threshold, score in thresholds:
            if bm >= threshold:
                return score
        return 20
    
    def _score_size(self, market_cap_usd: float) -> float:
        """Score by size. Smaller companies = higher expected returns."""
        thresholds = [
            (50_000_000, 100),     # < $50M nano-cap
            (250_000_000, 85),     # < $250M micro-cap (sweet spot)
            (500_000_000, 65),     # < $500M small-cap
            (1_000_000_000, 45),   # < $1B
            (2_000_000_000, 25),   # < $2B
        ]
        for threshold, score in thresholds:
            if market_cap_usd < threshold:
                return score
        return 10  # Above $2B
    
    def _score_profitability(self, roa: float, ebitda_margin: float) -> float:
        """
        Combined profitability score from ROA and EBITDA margin.
        Equal sub-weighting (50/50).
        """
        roa_score = self._score_threshold(
            roa, [(0.15, 100), (0.08, 75), (0.03, 50), (0.00, 25)], default=0
        )
        margin_score = self._score_threshold(
            ebitda_margin, [(0.25, 100), (0.15, 75), (0.08, 50), (0.00, 25)], default=0
        )
        return (roa_score * 0.5) + (margin_score * 0.5)
    
    def _score_investment_discipline(self, asset_growth: float, ebitda_growth: float) -> float:
        """
        Investment discipline: asset growth must not exceed EBITDA growth.
        When it does, next-year returns drop 4-11 percentage points.
        """
        if asset_growth > 0 and ebitda_growth > asset_growth:
            return 100  # Best: growing assets AND EBITDA growing faster
        elif asset_growth > 0 and ebitda_growth >= 0 and ebitda_growth >= asset_growth * 0.8:
            return 70   # Good: EBITDA roughly keeping pace
        elif asset_growth > 0 and ebitda_growth >= 0:
            return 30   # Caution: assets outpacing EBITDA
        elif asset_growth > 0 and ebitda_growth < 0:
            return 0    # Red flag: growing assets, shrinking EBITDA
        elif asset_growth <= 0 and ebitda_growth > 0:
            return 60   # Shrinking assets but growing EBITDA — efficiency play
        else:
            return 20   # Both shrinking
    
    def _score_price_position(self, position: float) -> float:
        """
        Score based on position in 52-week range.
        Near lows = high score. Near highs = low score (strong negative predictor).
        """
        thresholds = [(0.15, 100), (0.30, 80), (0.50, 50), (0.75, 25)]
        for threshold, score in thresholds:
            if position <= threshold:
                return score
        return 0
    
    # ── Anti-Multibagger Check ───────────────────────────────────────
    
    def _check_anti_multibagger(self, d: CompanyData) -> bool:
        """
        The anti-multibagger profile: overvalued + unprofitable + shrinking.
        This combination lost 18.1% annually in the study. Hard reject.
        """
        bm = self._calc_book_to_market(d)
        roa = self._calc_roa(d)
        asset_growth = self._calc_asset_growth(d)
        
        is_overvalued = bm < 0.40
        is_unprofitable = roa < 0
        is_shrinking = asset_growth < 0
        
        return is_overvalued and is_unprofitable and is_shrinking
    
    # ── Composite Score ──────────────────────────────────────────────
    
    def _compute_composite(self, result: ScoringResult) -> float:
        """Weighted composite score across all factors."""
        w = self.WEIGHTS
        return (
            result.fcf_yield_score * w["fcf_yield"]
            + result.book_to_market_score * w["book_to_market"]
            + result.size_score * w["size"]
            + result.profitability_score * w["profitability"]
            + result.investment_discipline_score * w["investment_discipline"]
            + result.price_position_score * w["price_position"]
        )
    
    # ── Utility ──────────────────────────────────────────────────────
    
    @staticmethod
    def _score_threshold(value: float, thresholds: list, default: float = 0) -> float:
        """Generic threshold-based scoring."""
        for threshold, score in thresholds:
            if value >= threshold:
                return score
        return default
