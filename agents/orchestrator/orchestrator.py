"""
FinSentinel AI - Master Orchestrator Agent
Routes tasks to specialized sub-agents, manages state, handles failures.
"""
from __future__ import annotations
import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import BaseTool

from config.settings import get_settings
from llm.providers.factory import get_llm_provider, CachedLLMClient
from security.audit.logger import AuditLogger
from security.pii.redactor import PIIRedactor

logger = logging.getLogger(__name__)


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    ESCALATED = "escalated"


@dataclass
class AgentTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    status: AgentStatus = AgentStatus.PENDING
    result: Optional[dict] = None
    error: Optional[str] = None
    retries: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    requires_approval: bool = False
    approved_by: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)


ORCHESTRATOR_SYSTEM_PROMPT = """You are FinSentinel's Master Orchestrator Agent — an expert AI system 
for Banking and Financial Services.

Your responsibilities:
1. Analyze incoming financial tasks and route them to the correct specialist agent
2. Coordinate multi-agent workflows when tasks span multiple domains
3. Enforce human-in-the-loop approval for high-risk decisions
4. Maintain auditability of every decision

Available specialist agents:
- fraud_detection_agent: Analyzes transactions for fraud patterns, anomalies, risk scoring
- transaction_analysis_agent: Categorizes, enriches, and summarizes transaction data
- customer_service_agent: Handles customer queries, account issues, policy lookups
- financial_insights_agent: Generates reports, trends, portfolio insights
- compliance_agent: Checks regulatory compliance, AML, KYC workflows

Rules:
- ALWAYS redact PII before processing
- Flag transactions > $50,000 for human approval
- Log every decision with reasoning
- If uncertain, escalate rather than guess
- Never fabricate financial data

Use the ReAct framework: Reason → Act → Observe → Repeat until task is complete.
"""


class OrchestratorAgent:
    """
    Master orchestrator. Manages task lifecycle, routes to sub-agents,
    handles retries, human-in-the-loop, and audit logging.
    """

    def __init__(self):
        self.settings = get_settings()
        self.provider = get_llm_provider(self.settings)
        self.llm = self.provider.get_chat_model()
        self.llm_client = CachedLLMClient(
            provider=self.provider,
            redis_url=self.settings.REDIS_URL,
            ttl=self.settings.LLM_CACHE_TTL,
        )
        self.pii_redactor = PIIRedactor()
        self.audit_logger = AuditLogger()
        self._task_store: dict[str, AgentTask] = {}

    async def submit_task(self, task_type: str, payload: dict, user_id: str) -> AgentTask:
        """Entry point: submit a new task to the orchestrator."""
        # Redact PII from payload before any processing
        clean_payload = self.pii_redactor.redact(payload)

        task = AgentTask(task_type=task_type, payload=clean_payload)
        task.metadata["submitted_by"] = user_id
        self._task_store[task.task_id] = task

        await self.audit_logger.log(
            event="task_submitted",
            task_id=task.task_id,
            user_id=user_id,
            task_type=task_type,
        )

        # Determine if task needs human approval
        task.requires_approval = self._requires_human_approval(task)
        if task.requires_approval:
            task.status = AgentStatus.AWAITING_APPROVAL
            logger.info(f"Task {task.task_id} flagged for human approval.")
            return task

        asyncio.create_task(self._execute_with_retry(task))
        return task

    async def approve_task(self, task_id: str, approver_id: str) -> AgentTask:
        """Human-in-the-loop: approve a pending task."""
        task = self._task_store.get(task_id)
        if not task or task.status != AgentStatus.AWAITING_APPROVAL:
            raise ValueError(f"Task {task_id} not found or not awaiting approval.")

        task.approved_by = approver_id
        task.status = AgentStatus.PENDING
        await self.audit_logger.log(
            event="task_approved", task_id=task_id, approver_id=approver_id
        )
        asyncio.create_task(self._execute_with_retry(task))
        return task

    async def get_task_status(self, task_id: str) -> AgentTask:
        task = self._task_store.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found.")
        return task

    def _requires_human_approval(self, task: AgentTask) -> bool:
        """Business rules for human-in-the-loop triggers."""
        payload = task.payload
        amount = payload.get("amount", 0)
        if amount and float(amount) > 50_000:
            return True
        if task.task_type in ("block_account", "approve_loan", "aml_flag"):
            return True
        return False

    async def _execute_with_retry(self, task: AgentTask) -> None:
        """Execute task with exponential backoff retry logic."""
        task.status = AgentStatus.RUNNING
        task.updated_at = datetime.utcnow()

        for attempt in range(task.max_retries):
            try:
                result = await self._route_and_execute(task)
                task.result = result
                task.status = AgentStatus.COMPLETED
                await self.audit_logger.log(
                    event="task_completed",
                    task_id=task.task_id,
                    result_summary=str(result)[:200],
                )
                return
            except Exception as exc:
                task.retries += 1
                task.error = str(exc)
                logger.warning(
                    f"Task {task.task_id} attempt {attempt+1} failed: {exc}"
                )
                if attempt < task.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff

        task.status = AgentStatus.FAILED
        task.status = AgentStatus.ESCALATED
        await self.audit_logger.log(
            event="task_escalated",
            task_id=task.task_id,
            error=task.error,
        )

    async def _route_and_execute(self, task: AgentTask) -> dict:
        """Use LLM to reason about routing, then invoke the correct agent."""
        routing_prompt = f"""
Task Type: {task.task_type}
Payload Summary: {str(task.payload)[:500]}

Which specialist agent should handle this task?
Respond with JSON: {{"agent": "<agent_name>", "reasoning": "<why>", "priority": "<low|medium|high>"}}
"""
        routing_response = await self.llm_client.invoke(
            system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
            user_message=routing_prompt,
            use_cache=False,
        )

        # Dynamically import and invoke the selected agent
        agent_map = {
            "fraud_detection_agent": self._invoke_fraud_agent,
            "transaction_analysis_agent": self._invoke_transaction_agent,
            "customer_service_agent": self._invoke_customer_agent,
            "financial_insights_agent": self._invoke_insights_agent,
        }

        import json, re
        try:
            match = re.search(r'\{.*\}', routing_response, re.DOTALL)
            routing = json.loads(match.group()) if match else {}
            agent_key = routing.get("agent", "transaction_analysis_agent")
        except Exception:
            agent_key = "transaction_analysis_agent"

        handler = agent_map.get(agent_key, self._invoke_transaction_agent)
        return await handler(task)

    async def _invoke_fraud_agent(self, task: AgentTask) -> dict:
        from agents.fraud.fraud_agent import FraudDetectionAgent
        agent = FraudDetectionAgent()
        return await agent.analyze(task.payload)

    async def _invoke_transaction_agent(self, task: AgentTask) -> dict:
        from agents.transaction.transaction_agent import TransactionAnalysisAgent
        agent = TransactionAnalysisAgent()
        return await agent.analyze(task.payload)

    async def _invoke_customer_agent(self, task: AgentTask) -> dict:
        from agents.customer.customer_agent import CustomerServiceAgent
        agent = CustomerServiceAgent()
        return await agent.handle(task.payload)

    async def _invoke_insights_agent(self, task: AgentTask) -> dict:
        from agents.insights.insights_agent import FinancialInsightsAgent
        agent = FinancialInsightsAgent()
        return await agent.generate(task.payload)
