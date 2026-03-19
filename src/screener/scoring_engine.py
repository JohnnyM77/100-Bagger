import logging

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS = {
    "fcf_yield":              0.30,
    "book_to_market":         0.20,
    "size":                   0.15,
    "roa":                    0.10,
    "ebitda_margin":          0.10,
    "investment_discipline":  0.10,
    "price_dislocation":      0.05,
}


class ScoringEngine:
    def __init__(self, weights: dict = None):
        self.weights = weights or DEFAULT_WEIGHTS

    def score(self, data: dict) -> tuple:
        """
        Scores a stock 0-100 across 7 empirically-validated dimensions.
        Returns (total_score: float, breakdown: dict).
        """
        breakdown = {
            "fcf_yield":             self._score_fcf_yield(data),
            "book_to_market":        self._score_book_to_market(data),
            "size":                  self._score_size(data),
            "roa":                   self._score_roa(data),
            "ebitda_margin":         self._score_ebitda_margin(data),
            "investment_discipline": self._score_investment_discipline(data),
            "price_dislocation":     self._score_price_dislocation(data),
        }

        total = sum(
            breakdown[dim] * self.weights.get(dim, 0)
            for dim in breakdown
        ) * 10

        return round(total, 2), breakdown

    def _score_fcf_yield(self, data: dict) -> float:
        """0-10. Higher FCF/P is better. Max score at FCF yield >= 10%."""
        val = data.get("fcf_yield", 0)
        if val <= 0:
            return 0.0
        if val >= 0.10:
            return 10.0
        return round(val / 0.10 * 10, 2)

    def _score_book_to_market(self, data: dict) -> float:
        """0-10. Higher B/M = better value. Max at B/M >= 1.0."""
        val = data.get("book_to_market", 0)
        if val <= 0:
            return 0.0
        if val >= 1.0:
            return 10.0
        return round(val / 1.0 * 10, 2)

    def _score_size(self, data: dict) -> float:
        """0-10. Sweet spot is $50M-$250M market cap."""
        cap = data.get("market_cap", 0)
        if not cap:
            return 0.0
        cap_m = cap / 1_000_000
        if 50 <= cap_m <= 250:
            return 10.0
        elif cap_m < 50:
            return round(max(0, cap_m / 50 * 8), 2)
        else:
            return round(max(0, 10 - (cap_m - 250) / 1750 * 10), 2)

    def _score_roa(self, data: dict) -> float:
        """0-10. Higher ROA is better. Max at ROA >= 15%."""
        val = data.get("roa", 0)
        if val <= 0:
            return 0.0
        if val >= 0.15:
            return 10.0
        return round(val / 0.15 * 10, 2)

    def _score_ebitda_margin(self, data: dict) -> float:
        """0-10. Higher EBITDA margin is better. Max at >= 30%."""
        rev = data.get("revenue_ttm", 0)
        ebitda = data.get("ebitda_ttm", 0)
        if not rev or ebitda <= 0:
            return 0.0
        margin = ebitda / rev
        if margin >= 0.30:
            return 10.0
        return round(margin / 0.30 * 10, 2)

    def _score_investment_discipline(self, data: dict) -> float:
        """0-10. Lower asset growth relative to EBITDA growth = better discipline."""
        asset_growth = data.get("asset_growth", 0)
        ebitda_growth = data.get("ebitda_growth", 0)
        if asset_growth <= 0:
            return 10.0
        if ebitda_growth > 0:
            ratio = asset_growth / ebitda_growth
            if ratio <= 0.5:
                return 10.0
            elif ratio <= 1.0:
                return 7.0
            elif ratio <= 1.5:
                return 4.0
            else:
                return 1.0
        return 3.0

    def _score_price_dislocation(self, data: dict) -> float:
        """0-10. Further from 52-week high = higher score (Overreaction Hypothesis)."""
        current = data.get("current_price", 0)
        high = data.get("price_52w_high", 0)
        if not high or not current:
            return 5.0
        ratio = current / high
        if ratio >= 0.95:
            return 0.0
        elif ratio >= 0.80:
            return 4.0
        elif ratio >= 0.60:
            return 7.0
        else:
            return 10.0
