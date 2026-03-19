"""
FinSentinel AI - Customer Service Agent
Handles customer queries with RAG-powered policy lookup and empathetic responses.
"""
from __future__ import annotations
import logging
from typing import Any

from config.settings import get_settings
from llm.providers.factory import get_llm_provider, CachedLLMClient

logger = logging.getLogger(__name__)

CUSTOMER_SYSTEM_PROMPT = """You are FinSentinel's Customer Service Agent — a knowledgeable, 
empathetic banking assistant.

Your capabilities:
- Answer account and product questions using the bank's policy knowledge base
- Explain charges, fees, and transactions in plain language
- Guide customers through dispute and complaint processes
- Provide personalized financial guidance

Rules:
- Never share account details you don't have in context
- Never make up policy information — say "I'll check that for you"
- Always be empathetic and professional
- Escalate to human agent if customer expresses frustration 3+ times
- Do NOT discuss competitor banks

Response format: Plain, conversational English. Always end with a follow-up question.
"""


class CustomerServiceAgent:
    def __init__(self):
        self.settings = get_settings()
        self.provider = get_llm_provider(self.settings)
        self.llm_client = CachedLLMClient(
            provider=self.provider,
            redis_url=self.settings.REDIS_URL,
            ttl=300,
        )

    async def handle(self, payload: dict[str, Any]) -> dict:
        query = payload.get("query", "")
        customer_context = payload.get("customer_context", {})
        conversation_history = payload.get("history", [])

        context_str = f"Customer Profile: {customer_context}" if customer_context else ""
        history_str = "\n".join(
            [f"{m['role'].upper()}: {m['content']}" for m in conversation_history[-5:]]
        )

        user_message = f"""
{context_str}

Conversation History:
{history_str}

Current Query: {query}

Please respond helpfully.
"""
        response = await self.llm_client.invoke(
            system_prompt=CUSTOMER_SYSTEM_PROMPT,
            user_message=user_message,
        )

        requires_escalation = any(
            phrase in query.lower()
            for phrase in ["speak to human", "manager", "complaint", "unacceptable"]
        )

        return {
            "response": response,
            "requires_escalation": requires_escalation,
            "channel": "ai_chat",
            "agent": "customer_service_agent",
        }
