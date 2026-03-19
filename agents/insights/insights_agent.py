"""
FinSentinel AI - Financial Insights Agent
Generates intelligent reports, spend summaries, and financial health assessments.
"""
from __future__ import annotations
import json
import logging
import re
from typing import Any

from config.settings import get_settings
from llm.providers.factory import get_llm_provider, CachedLLMClient

logger = logging.getLogger(__name__)

INSIGHTS_SYSTEM_PROMPT = """You are FinSentinel's Financial Insights Agent — a senior financial analyst AI.

You generate:
- Monthly/quarterly spend summaries with trend analysis
- Budget vs actual variance reports
- Cash flow forecasting (based on historical patterns)
- Savings opportunity identification
- Risk exposure assessments

Always back insights with the data provided. Never extrapolate beyond the data.
Provide actionable, specific recommendations. Use percentages and numbers.
Return structured JSON unless asked for narrative.
"""


class FinancialInsightsAgent:
    def __init__(self):
        self.settings = get_settings()
        self.provider = get_llm_provider(self.settings)
        self.llm_client = CachedLLMClient(
            provider=self.provider,
            redis_url=self.settings.REDIS_URL,
            ttl=3600,
        )

    async def generate(self, payload: dict[str, Any]) -> dict:
        report_type = payload.get("report_type", "spend_summary")
        data = payload.get("data", {})
        period = payload.get("period", "monthly")

        prompt = f"""
Generate a {report_type} report for period: {period}

Input Data:
{json.dumps(data, indent=2)}

Return JSON with:
{{
  "report_type": "{report_type}",
  "period": "{period}",
  "executive_summary": "<2-3 sentence overview>",
  "key_metrics": {{
    "total_spend": <number>,
    "top_category": "<category>",
    "month_over_month_change": "<+/-X%>",
    "savings_rate": "<X%>"
  }},
  "category_breakdown": [
    {{"category": "<name>", "amount": <number>, "percentage": <number>, "trend": "<up|down|stable>"}}
  ],
  "insights": ["<insight1>", "<insight2>", "<insight3>"],
  "recommendations": ["<rec1>", "<rec2>"],
  "risk_flags": ["<flag1>"]
}}
"""
        response = await self.llm_client.invoke(
            system_prompt=INSIGHTS_SYSTEM_PROMPT,
            user_message=prompt,
        )

        try:
            match = re.search(r'\{.*\}', response, re.DOTALL)
            return json.loads(match.group()) if match else {"raw": response}
        except Exception as e:
            logger.error(f"[InsightsAgent] Parse error: {e}")
            return {"error": str(e), "raw": response}
