"""
FinSentinel AI - Kafka Transaction Consumer
Real-time event-driven transaction ingestion and processing.
"""
from __future__ import annotations
import asyncio
import json
import logging
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class TransactionStreamConsumer:
    """
    Consumes real-time transaction events from Kafka.
    Routes each event to the fraud detection pipeline.
    Emits alerts back to Kafka on high-risk detections.
    """

    def __init__(self):
        self.consumer: AIOKafkaConsumer | None = None
        self.producer: AIOKafkaProducer | None = None
        self.running = False

    async def start(self):
        self.consumer = AIOKafkaConsumer(
            settings.KAFKA_TOPIC_TRANSACTIONS,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            group_id=settings.KAFKA_GROUP_ID,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            auto_offset_reset="latest",
            enable_auto_commit=True,
        )
        self.producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await self.consumer.start()
        await self.producer.start()
        self.running = True
        logger.info(f"Kafka consumer started on topic: {settings.KAFKA_TOPIC_TRANSACTIONS}")

    async def stop(self):
        self.running = False
        if self.consumer:
            await self.consumer.stop()
        if self.producer:
            await self.producer.stop()

    async def process_stream(self):
        """Main event loop: consume → analyze → emit alerts."""
        from agents.fraud.fraud_agent import FraudDetectionAgent
        fraud_agent = FraudDetectionAgent()

        async for message in self.consumer:
            if not self.running:
                break
            try:
                transaction: dict[str, Any] = message.value
                logger.debug(f"Processing transaction: {transaction.get('transaction_id')}")

                result = await fraud_agent.analyze(transaction)
                risk_score = result.get("risk_score", 0)

                if risk_score >= 61:
                    alert = {
                        "transaction_id": transaction.get("transaction_id"),
                        "risk_score": risk_score,
                        "risk_level": result.get("risk_level"),
                        "recommended_action": result.get("recommended_action"),
                        "fraud_patterns": result.get("fraud_patterns", []),
                        "timestamp": transaction.get("timestamp"),
                    }
                    await self.producer.send(settings.KAFKA_TOPIC_ALERTS, alert)
                    logger.warning(
                        f"[ALERT] High-risk transaction {transaction.get('transaction_id')} "
                        f"risk={risk_score}"
                    )

            except Exception as exc:
                logger.error(f"Error processing Kafka message: {exc}", exc_info=True)
                # Commit offset anyway to avoid infinite retry loops on bad messages


async def run_consumer():
    consumer = TransactionStreamConsumer()
    await consumer.start()
    try:
        await consumer.process_stream()
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_consumer())
