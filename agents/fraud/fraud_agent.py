"""
FinSentinel AI - Fraud Detection Agent
Real-time fraud risk scoring using LLM + rules + RAG context.
"""
from __future__ import annotations
import logging
from typing import Any

from config.settings import get_settings
from llm.providers.factory import get_llm_provider, CachedLLMClient

logger = logging.getLogger(__name__)

FRAUD_SYSTEM_PROMPT = """You are FinSentinel's Fraud Detection Agent — an expert in financial fraud analysis.

Your job:
1. Analyze transaction data for fraud signals
2. Score risk from 0-100 (0=safe, 100=definite fraud)
3. Identify specific fraud patterns (velocity, geo-anomaly, card-not-present, account takeover)
4. Provide clear reasoning and recommended actions

Risk Thresholds:
- 0-30: Low risk → Auto-approve
- 31-60: Medium risk → Flag for review
- 61-80: High risk → Block + notify customer
- 81-100: Critical → Block + escalate to fraud team

Always respond in structured JSON format.
"""


class FraudDetectionAgent:
    def __init__(self):
        self.settings = get_settings()
        self.provider = get_llm_provider(self.settings)
        self.llm_client = CachedLLMClient(
            provider=self.provider,
            redis_url=self.settings.REDIS_URL,
        )

    async def analyze(self, transaction: dict[str, Any]) -> dict:
        """Analyze a transaction for fraud risk."""
        import json

        prompt = f"""
Analyze this financial transaction for fraud:

Transaction Data:
{json.dumps(transaction, indent=2)}

Evaluate:
1. Transaction amount vs account history
2. Geographic anomalies (IP location vs billing address)
3. Velocity patterns (frequency of recent transactions)
4. Merchant category risk
5. Time-of-day patterns
6. Device fingerprint anomalies

Return ONLY valid JSON:
{{
  "risk_score": <0-100>,
  "risk_level": "<low|medium|high|critical>",
  "fraud_patterns": ["<pattern1>", "<pattern2>"],
  "confidence": <0.0-1.0>,
  "recommended_action": "<approve|review|block|escalate>",
  "reasoning": "<detailed explanation>",
  "flags": {{
    "velocity_anomaly": <true|false>,
    "geo_anomaly": <true|false>,
    "amount_anomaly": <true|false>,
    "device_anomaly": <true|false>
  }}
}}
"""
        response = await self.llm_client.invoke(
            system_prompt=FRAUD_SYSTEM_PROMPT,
            user_message=prompt,
            use_cache=False,  # Never cache fraud analysis
        )

        try:
            import re
            match = re.search(r'\{.*\}', response, re.DOTALL)
            result = json.loads(match.group()) if match else {}
        except Exception as e:
            logger.error(f"Failed to parse fraud response: {e}")
            result = {
                "risk_score": 50,
                "risk_level": "medium",
                "recommended_action": "review",
                "reasoning": "Parse error — defaulting to manual review",
                "error": str(e),
            }

        logger.info(
            f"[FraudAgent] tx={transaction.get('transaction_id', 'N/A')} "
            f"risk={result.get('risk_score', 'N/A')} "
            f"action={result.get('recommended_action', 'N/A')}"
        )
        return result
