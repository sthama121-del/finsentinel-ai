"""
FinSentinel AI - Transaction Analysis Agent
Categorization, enrichment, and insight generation for financial transactions.
"""
from __future__ import annotations
import json
import logging
import re
from typing import Any

from config.settings import get_settings
from llm.providers.factory import get_llm_provider, CachedLLMClient

logger = logging.getLogger(__name__)

TRANSACTION_SYSTEM_PROMPT = """You are FinSentinel's Transaction Analysis Agent.
You categorize and enrich financial transactions with business intelligence.

Your capabilities:
- Merchant categorization (MCC codes, business type)
- Spend pattern analysis
- Budget impact assessment
- Anomaly flagging (unusual amounts, new merchants)
- Tax category tagging

Always return structured JSON. Be precise and concise.
"""


class TransactionAnalysisAgent:
    def __init__(self):
        self.settings = get_settings()
        self.provider = get_llm_provider(self.settings)
        self.llm_client = CachedLLMClient(
            provider=self.provider,
            redis_url=self.settings.REDIS_URL,
            ttl=1800,
        )

    async def analyze(self, transaction: dict[str, Any]) -> dict:
        prompt = f"""
Analyze and enrich this transaction:
{json.dumps(transaction, indent=2)}

Return JSON:
{{
  "category": "<Food|Travel|Healthcare|Entertainment|Utilities|Shopping|Transfer|Other>",
  "subcategory": "<specific subcategory>",
  "merchant_type": "<business type>",
  "is_recurring": <true|false>,
  "is_unusual": <true|false>,
  "tax_deductible_likelihood": "<none|possible|likely>",
  "spend_impact": "<low|medium|high>",
  "summary": "<one-line human-readable summary>",
  "tags": ["<tag1>", "<tag2>"]
}}
"""
        response = await self.llm_client.invoke(
            system_prompt=TRANSACTION_SYSTEM_PROMPT,
            user_message=prompt,
        )

        try:
            match = re.search(r'\{.*\}', response, re.DOTALL)
            return json.loads(match.group()) if match else {"raw": response}
        except Exception as e:
            logger.error(f"[TransactionAgent] Parse error: {e}")
            return {"error": str(e), "raw": response}
