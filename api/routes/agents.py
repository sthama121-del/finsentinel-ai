"""
FinSentinel AI - Agent API Routes
Endpoints for task submission, status, and approval workflows.
"""
from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Any, Optional

from agents.orchestrator.orchestrator import OrchestratorAgent

router = APIRouter()
_orchestrator = OrchestratorAgent()


class TaskRequest(BaseModel):
    task_type: str
    payload: dict[str, Any]

class ApprovalRequest(BaseModel):
    approver_id: str


@router.post("/tasks")
async def submit_task(
    request: TaskRequest,
    x_user_id: str = Header(default="anonymous"),
):
    """Submit a task to the AI orchestrator."""
    task = await _orchestrator.submit_task(
        task_type=request.task_type,
        payload=request.payload,
        user_id=x_user_id,
    )
    return {
        "task_id": task.task_id,
        "status": task.status,
        "requires_approval": task.requires_approval,
        "message": "Task submitted successfully",
    }


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get the status and result of a submitted task."""
    try:
        task = await _orchestrator.get_task_status(task_id)
        return {
            "task_id": task.task_id,
            "status": task.status,
            "result": task.result,
            "error": task.error,
            "retries": task.retries,
            "requires_approval": task.requires_approval,
            "approved_by": task.approved_by,
            "created_at": task.created_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/tasks/{task_id}/approve")
async def approve_task(task_id: str, request: ApprovalRequest):
    """Human-in-the-loop: approve a high-risk task."""
    try:
        task = await _orchestrator.approve_task(task_id, request.approver_id)
        return {"task_id": task.task_id, "status": task.status, "message": "Task approved"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/fraud/analyze")
async def analyze_fraud(
    payload: dict[str, Any],
    x_user_id: str = Header(default="anonymous"),
):
    """Direct fraud analysis endpoint (bypasses orchestrator for speed)."""
    from agents.fraud.fraud_agent import FraudDetectionAgent
    agent = FraudDetectionAgent()
    result = await agent.analyze(payload)
    return result
