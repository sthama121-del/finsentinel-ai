"""
FinSentinel AI - DAG 5: Audit Log Archival & Compliance
Runs daily at 1 AM. Archives old audit logs, generates compliance summary.
"""
from __future__ import annotations

from datetime import timedelta
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.dates import days_ago

log = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "finsentinel-compliance",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def archive_old_audit_logs(**context) -> dict:
    """Move audit logs older than 30 days to archive table."""
    import psycopg2, os

    conn = psycopg2.connect(os.getenv("POSTGRES_URL", "postgresql://finuser:finpass@postgres:5432/finsentinel"))
    cursor = conn.cursor()

    # Create archive table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs_archive
        (LIKE audit_logs INCLUDING ALL)
    """)

    # Move old records
    cursor.execute("""
        WITH moved AS (
            DELETE FROM audit_logs
            WHERE created_at < NOW() - INTERVAL '30 days'
            RETURNING *
        )
        INSERT INTO audit_logs_archive SELECT * FROM moved
    """)

    archived = cursor.rowcount
    conn.commit()
    conn.close()

    log.info(f"[Audit Archive] Archived {archived} old audit log records")
    context["task_instance"].xcom_push(key="archived_count", value=archived)
    return {"archived": archived}


def generate_compliance_report(**context) -> dict:
    """Generate daily compliance summary: task counts, fraud alerts, approvals."""
    import psycopg2, os, json
    from datetime import date

    conn = psycopg2.connect(os.getenv("POSTGRES_URL", "postgresql://finuser:finpass@postgres:5432/finsentinel"))
    cursor = conn.cursor()

    yesterday = (date.today() - timedelta(days=1)).isoformat()

    cursor.execute("""
        SELECT event, COUNT(*) as count
        FROM audit_logs
        WHERE DATE(timestamp) = %s
        GROUP BY event
        ORDER BY count DESC
    """, (yesterday,))

    event_counts = {row[0]: row[1] for row in cursor.fetchall()}

    cursor.execute("""
        SELECT COUNT(*) FROM agent_tasks
        WHERE DATE(created_at) = %s AND requires_approval = TRUE
    """, (yesterday,))
    approval_tasks = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM fraud_alerts
        WHERE DATE(created_at) = %s AND resolved = FALSE
    """, (yesterday,))
    unresolved_alerts = cursor.fetchone()[0]

    conn.close()

    report = {
        "date": yesterday,
        "audit_events": event_counts,
        "approval_tasks": approval_tasks,
        "unresolved_fraud_alerts": unresolved_alerts,
        "compliance_status": "review_required" if unresolved_alerts > 0 else "clear",
    }

    context["task_instance"].xcom_push(key="compliance_report", value=report)
    log.info(f"[Compliance] Report generated: {json.dumps(report)}")
    return report


def publish_compliance_to_kafka(**context) -> dict:
    """Publish compliance report to Kafka for downstream consumers."""
    import json, os
    from kafka import KafkaProducer

    report = context["task_instance"].xcom_pull(
        task_ids="generate_compliance_report", key="compliance_report"
    )

    try:
        producer = KafkaProducer(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092"),
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        producer.send("fin.audit.logs", {"type": "compliance_report", **report})
        producer.flush()
        producer.close()
        log.info("[Compliance Kafka] Published compliance report")
        return {"published": True}
    except Exception as e:
        log.warning(f"Kafka publish failed (non-fatal): {e}")
        return {"published": False, "error": str(e)}


with DAG(
    dag_id="audit_log_archival_compliance",
    description="Daily audit log archival and compliance summary generation",
    default_args=DEFAULT_ARGS,
    schedule_interval="0 1 * * *",     # 1 AM daily
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["finsentinel", "audit", "compliance", "daily"],
) as dag:

    start = EmptyOperator(task_id="start")

    archive = PythonOperator(
        task_id="archive_old_audit_logs",
        python_callable=archive_old_audit_logs,
        provide_context=True,
    )

    compliance = PythonOperator(
        task_id="generate_compliance_report",
        python_callable=generate_compliance_report,
        provide_context=True,
    )

    publish = PythonOperator(
        task_id="publish_compliance_to_kafka",
        python_callable=publish_compliance_to_kafka,
        provide_context=True,
    )

    end = EmptyOperator(task_id="end")

    start >> archive >> compliance >> publish >> end
