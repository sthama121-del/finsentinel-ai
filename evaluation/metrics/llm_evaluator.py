"""
FinSentinel AI - LLM Evaluation Framework
Measures accuracy, hallucination risk, latency, and relevance of LLM responses.
"""
from __future__ import annotations
import time
import re
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class EvalResult:
    task_id: str
    provider: str
    model: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    relevance_score: float          # 0.0 – 1.0
    hallucination_risk: float       # 0.0 – 1.0 (lower is better)
    json_parse_success: bool
    confidence: float               # Model's own confidence if expressed
    notes: str = ""


class LLMEvaluator:
    """
    Lightweight evaluation harness for financial AI responses.
    In production: integrate with LangSmith or Azure AI Evaluation.
    """

    HALLUCINATION_MARKERS = [
        "i don't know", "i cannot confirm", "as of my knowledge",
        "i believe", "i think", "might be", "could be",
        "approximately", "roughly", "probably",
    ]

    FINANCIAL_CONFIDENCE_MARKERS = [
        "confirmed", "verified", "according to",
        "based on the provided", "from the data",
    ]

    def evaluate_response(
        self,
        task_id: str,
        provider: str,
        model: str,
        response: str,
        expected_keys: Optional[list[str]] = None,
        latency_ms: int = 0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
    ) -> EvalResult:
        """Evaluate a single LLM response."""

        # JSON parse success
        json_success = self._check_json_parse(response)

        # Hallucination risk: presence of uncertainty markers
        response_lower = response.lower()
        hallucination_count = sum(
            1 for marker in self.HALLUCINATION_MARKERS
            if marker in response_lower
        )
        hallucination_risk = min(hallucination_count / 5.0, 1.0)

        # Relevance: presence of financial confidence markers
        confidence_count = sum(
            1 for marker in self.FINANCIAL_CONFIDENCE_MARKERS
            if marker in response_lower
        )
        relevance_score = min(0.5 + (confidence_count * 0.15), 1.0)

        # Check for expected keys in JSON output
        if expected_keys and json_success:
            try:
                import json
                match = re.search(r'\{.*\}', response, re.DOTALL)
                parsed = json.loads(match.group()) if match else {}
                missing = [k for k in expected_keys if k not in parsed]
                if missing:
                    relevance_score *= 0.7
                    logger.warning(f"[Eval] Missing keys in response: {missing}")
            except Exception:
                pass

        result = EvalResult(
            task_id=task_id,
            provider=provider,
            model=model,
            latency_ms=latency_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            relevance_score=round(relevance_score, 3),
            hallucination_risk=round(hallucination_risk, 3),
            json_parse_success=json_success,
            confidence=round(1.0 - hallucination_risk, 3),
        )

        logger.info(
            f"[LLM Eval] task={task_id} provider={provider} "
            f"latency={latency_ms}ms relevance={relevance_score:.2f} "
            f"hallucination_risk={hallucination_risk:.2f}"
        )
        return result

    def _check_json_parse(self, response: str) -> bool:
        import json
        try:
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                json.loads(match.group())
                return True
        except Exception:
            pass
        return False

    def benchmark_providers(self, test_cases: list[dict]) -> dict:
        """
        Run eval across multiple test cases and aggregate results.
        Used for: provider comparison, regression testing, model upgrades.
        """
        results = {"total": 0, "passed": 0, "avg_latency_ms": 0, "avg_relevance": 0}
        latencies, relevances = [], []

        for case in test_cases:
            result = self.evaluate_response(**case)
            results["total"] += 1
            if result.json_parse_success and result.relevance_score >= 0.6:
                results["passed"] += 1
            latencies.append(result.latency_ms)
            relevances.append(result.relevance_score)

        results["avg_latency_ms"] = sum(latencies) / len(latencies) if latencies else 0
        results["avg_relevance"] = sum(relevances) / len(relevances) if relevances else 0
        results["pass_rate"] = results["passed"] / results["total"] if results["total"] else 0
        return results
