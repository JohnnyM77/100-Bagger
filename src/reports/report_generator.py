import logging
from pathlib import Path
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import anthropic

logger = logging.getLogger(__name__)

QUALITATIVE_PROMPT = """You are a senior equity analyst at a tier-1 fund.
Analyze this {exchange} small-cap stock for multibagger potential.

Company: {name} ({ticker})
Sector: {sector}
Market Cap: ${market_cap_m:.1f}M
FCF Yield: {fcf_yield:.1%}
Book-to-Market: {book_to_market:.2f}
ROA: {roa:.1%}
Score: {total_score:.0f}/100

Write ONLY the following sections in markdown, no preamble or commentary:

## Business model
[2 paragraphs on what this company actually does and why it could compound]

## Key risks
- [Risk 1]
- [Risk 2]
- [Risk 3]

## Bull case
[1 paragraph]

## Bear case
[1 paragraph]

## Potential catalysts
- [Catalyst 1]
- [Catalyst 2]
- [Catalyst 3]
"""


class ReportGenerator:
    def __init__(self, anthropic_api_key: str, template_path: str):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        template_dir = str(Path(template_path).parent)
        template_file = Path(template_path).name
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.template_file = template_file
        self.month_key = datetime.now().strftime("%Y-%m")

    def _get_qualitative(self, candidate: dict, total_score: float) -> str:
        prompt = QUALITATIVE_PROMPT.format(
            exchange=candidate.get("exchange", ""),
            name=candidate.get("name", ""),
            ticker=candidate.get("ticker", ""),
            sector=candidate.get("sector", ""),
            market_cap_m=candidate.get("market_cap", 0) / 1_000_000,
            fcf_yield=candidate.get("fcf_yield", 0),
            book_to_market=candidate.get("book_to_market", 0),
            roa=candidate.get("roa", 0),
            total_score=total_score,
        )
        try:
            message = self.client.messages.create(
                model="claude-opus-4-6",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
        except Exception as e:
            logger.warning(f"Claude API error for {candidate.get('ticker')}: {e}")
            return "_Qualitative analysis unavailable._"

    def generate_report(self, candidate: dict, score_breakdown: dict) -> str:
        total_score = candidate.get("score", 0)
        qualitative = self._get_qualitative(candidate, total_score)

        try:
            template = self.env.get_template(self.template_file)
            report = template.render(
                **candidate,
                score_breakdown=score_breakdown,
                total_score=total_score,
                qualitative=qualitative,
                generated_date=self.month_key,
            )
        except Exception as e:
            logger.warning(f"Template render error for {candidate.get('ticker')}: {e}")
            report = self._fallback_report(candidate, score_breakdown, qualitative, total_score)

        ticker = candidate.get("ticker", "UNKNOWN")
        exchange = candidate.get("exchange", "XX")
        out_path = Path("reports") / f"{exchange}_{ticker}_{self.month_key}.md"
        out_path.write_text(report)
        logger.info(f"  Report saved: {out_path}")
        return report

    def _fallback_report(self, candidate: dict, breakdown: dict, qualitative: str, score: float) -> str:
        lines = [
            f"# {candidate.get('name', '')} ({candidate.get('ticker', '')})",
            f"**Exchange:** {candidate.get('exchange', '')} | **Rank:** #{candidate.get('rank', '')} | **Score:** {score:.0f}/100",
            f"**Market Cap:** ${candidate.get('market_cap', 0)/1_000_000:.1f}M",
            f"**Sector:** {candidate.get('sector', '')}",
            "",
            "## Quantitative scores",
        ]
        for dim, val in breakdown.items():
            lines.append(f"- {dim.replace('_', ' ').title()}: {val:.1f}/10")
        lines += ["", qualitative]
        return "\n".join(lines)

    def generate_summary_table(self, all_candidates: list) -> str:
        lines = [
            f"# 100-Bagger screen summary — {self.month_key}",
            "",
            "| Rank | Ticker | Name | Exchange | Mkt Cap $M | FCF Yield | B/M | Score |",
            "|------|--------|------|----------|------------|-----------|-----|-------|",
        ]
        for c in all_candidates:
            lines.append(
                f"| {c.get('rank', '')}"
                f" | {c.get('ticker', '')}"
                f" | {c.get('name', '')}"
                f" | {c.get('exchange', '')}"
                f" | {c.get('market_cap', 0)/1_000_000:.0f}"
                f" | {c.get('fcf_yield', 0):.1%}"
                f" | {c.get('book_to_market', 0):.2f}"
                f" | {c.get('score', 0):.0f} |"
            )

        exchanges = list({c.get("exchange", "") for c in all_candidates})
        exchange_str = "_".join(sorted(exchanges))
        out_path = Path("reports") / f"summary_{exchange_str}_{self.month_key}.md"
        content = "\n".join(lines)
        out_path.write_text(content)
        logger.info(f"Summary table saved: {out_path}")
        return content
