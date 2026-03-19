"""
FinSentinel AI - DAG 2: Fraud Detection & Alert Generation
Triggered every 5 minutes. Scans high-value transactions, scores risk, generates alerts.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.dates import days_ago

log = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "finsentinel-fraud",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=1),
}


def fetch_unscored_transactions(**context) -> dict:
    """Fetch transactions not yet fraud-scored in last 24 hours."""
    import psycopg2, os, json

    conn = psycopg2.connect(os.getenv("POSTGRES_URL", "postgresql://finuser:finpass@postgres:5432/finsentinel"))
    cursor = conn.cursor()
    cursor.execute("""
        SELECT task_id, payload FROM agent_tasks
        WHERE task_type IN ('transaction_analysis', 'fraud_check')
        AND status = 'pending'
        AND created_at > NOW() - INTERVAL '24 hours'
        ORDER BY created_at DESC
        LIMIT 100
    """)
    rows = cursor.fetchall()
    conn.close()

    transactions = [{"task_id": r[0], "payload": r[1]} for r in rows]
    context["task_instance"].xcom_push(key="transactions", value=transactions)
    log.info(f"[Fraud] Fetched {len(transactions)} unscored transactions")
    return {"count": len(transactions)}


def run_fraud_scoring(**context) -> dict:
    """Run fraud agent on each transaction."""
    import sys, asyncio
    sys.path.insert(0, "/opt/airflow/dags")

    transactions = context["task_instance"].xcom_pull(
        task_ids="fetch_unscored_transactions", key="transactions"
    ) or []

    from agents.fraud.fraud_agent import FraudDetectionAgent
    agent = FraudDetectionAgent()
    scored = []

    async def run():
        for tx in transactions:
            try:
                result = await agent.analyze(tx["payload"])
                scored.append({
                    "task_id": tx["task_id"],
                    "risk_score": result.get("risk_score", 0),
                    "risk_level": result.get("risk_level", "low"),
                    "recommended_action": result.get("recommended_action", "approve"),
                    "fraud_patterns": result.get("fraud_patterns", []),
                    "reasoning": result.get("reasoning", ""),
                })
            except Exception as e:
                log.error(f"Scoring failed for {tx['task_id']}: {e}")

    asyncio.run(run())
    context["task_instance"].xcom_push(key="scored", value=scored)

    high_risk = [s for s in scored if s["risk_score"] >= 61]
    log.info(f"[Fraud] Scored {len(scored)} | High risk: {len(high_risk)}")
    return {"scored": len(scored), "high_risk": len(high_risk)}


def check_high_risk(**context) -> str:
    """Branch: route to alert path only if high-risk transactions exist."""
    scored = context["task_instance"].xcom_pull(
        task_ids="run_fraud_scoring", key="scored"
    ) or []
    high_risk = [s for s in scored if s["risk_score"] >= 61]
    if high_risk:
        return "generate_fraud_alerts"
    return "no_alerts_needed"


def generate_fraud_alerts(**context) -> dict:
    """Save fraud alerts to PostgreSQL and publish to Kafka."""
    import psycopg2, os, json
    from kafka import KafkaProducer

    scored = context["task_instance"].xcom_pull(
        task_ids="run_fraud_scoring", key="scored"
    ) or []
    high_risk = [s for s in scored if s["risk_score"] >= 61]

    # Save to DB
    conn = psycopg2.connect(os.getenv("POSTGRES_URL", "postgresql://finuser:finpass@postgres:5432/finsentinel"))
    cursor = conn.cursor()
    for alert in high_risk:
        cursor.execute("""
            INSERT INTO fraud_alerts
            (transaction_id, risk_score, risk_level, recommended_action, fraud_patterns, reasoning)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
        """, (
            alert["task_id"],
            alert["risk_score"],
            alert["risk_level"],
            alert["recommended_action"],
            json.dumps(alert["fraud_patterns"]),
            alert["reasoning"],
        ))
    conn.commit()
    conn.close()

    # Publish to Kafka
    try:
        producer = KafkaProducer(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092"),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        for alert in high_risk:
            producer.send("fin.alerts", alert)
        producer.flush()
        producer.close()
    except Exception as e:
        log.warning(f"Kafka publish failed (non-fatal): {e}")

    log.info(f"[Fraud Alerts] Generated {len(high_risk)} alerts")
    return {"alerts_generated": len(high_risk)}


def notify_fraud_team(**context) -> None:
    """Notify fraud team — hook for email/Slack/webhook in production."""
    scored = context["task_instance"].xcom_pull(
        task_ids="run_fraud_scoring", key="scored"
    ) or []
    critical = [s for s in scored if s["risk_score"] >= 81]
    if critical:
        log.warning(f"[CRITICAL FRAUD] {len(critical)} critical risk transactions detected!")
        # In production: send email, Slack webhook, PagerDuty alert


with DAG(
    dag_id="fraud_detection_alert_pipeline",
    description="Score transactions for fraud risk and generate alerts for high-risk cases",
    default_args=DEFAULT_ARGS,
    schedule_interval="*/5 * * * *",    # Every 5 minutes
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["finsentinel", "fraud", "alerts", "critical"],
) as dag:

    start = EmptyOperator(task_id="start")

    fetch = PythonOperator(
        task_id="fetch_unscored_transactions",
        python_callable=fetch_unscored_transactions,
        provide_context=True,
    )

    score = PythonOperator(
        task_id="run_fraud_scoring",
        python_callable=run_fraud_scoring,
        provide_context=True,
        execution_timeout=timedelta(minutes=8),
    )

    branch = BranchPythonOperator(
        task_id="check_high_risk",
        python_callable=check_high_risk,
        provide_context=True,
    )

    alerts = PythonOperator(
        task_id="generate_fraud_alerts",
        python_callable=generate_fraud_alerts,
        provide_context=True,
    )

    notify = PythonOperator(
        task_id="notify_fraud_team",
        python_callable=notify_fraud_team,
        provide_context=True,
    )

    no_alerts = EmptyOperator(task_id="no_alerts_needed")
    end = EmptyOperator(task_id="end", trigger_rule="none_failed_min_one_success")

    start >> fetch >> score >> branch
    branch >> alerts >> notify >> end
    branch >> no_alerts >> end
