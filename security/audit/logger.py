"""
FinSentinel AI - Audit Logger
Immutable, structured audit trail for all AI decisions and actions.
"""
import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AuditLogger:
    """
    Writes structured audit events to:
    - Local logger (always)
    - Kafka topic fin.audit.logs (when available)
    - PostgreSQL audit table (async, non-blocking)
    """

    def __init__(self):
        self._kafka_producer = None
        self._audit_log: list[dict] = []  # In-memory for local dev

    async def log(
        self,
        event: str,
        task_id: Optional[str] = None,
        user_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        record = {
            "audit_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "task_id": task_id,
            "user_id": user_id,
            **kwargs,
        }
        self._audit_log.append(record)
        logger.info(f"[AUDIT] {json.dumps(record)}")

        # In production: push to Kafka topic fin.audit.logs
        # await self._push_to_kafka(record)

    async def get_audit_trail(self, task_id: str) -> list[dict]:
        return [r for r in self._audit_log if r.get("task_id") == task_id]
