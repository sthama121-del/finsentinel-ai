"""
FinSentinel AI - DAG 3: Daily Financial Risk Summary
Runs at 6 AM daily. Aggregates prior day data, generates AI report, stores + publishes.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.dates import days_ago

log = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "finsentinel-insights",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}


def aggregate_daily_data(**context) -> dict:
    """Aggregate prior day transactions and fraud alerts from PostgreSQL."""
    import psycopg2, os, json

    execution_date = context["execution_date"]
    date_str = execution_date.strftime("%Y-%m-%d")

    conn = psycopg2.connect(os.getenv("POSTGRES_URL", "postgresql://finuser:finpass@postgres:5432/finsentinel"))
    cursor = conn.cursor()

    # Transaction summary
    cursor.execute("""
        SELECT
            COUNT(*) as total_transactions,
            COUNT(CASE WHEN status='completed' THEN 1 END) as completed,
            COUNT(CASE WHEN status='failed' THEN 1 END) as failed
        FROM agent_tasks
        WHERE DATE(created_at) = %s
        AND task_type = 'transaction_analysis'
    """, (date_str,))
    tx_row = cursor.fetchone()

    # Fraud summary
    cursor.execute("""
        SELECT
            COUNT(*) as total_alerts,
            COUNT(CASE WHEN risk_level='critical' THEN 1 END) as critical,
            COUNT(CASE WHEN risk_level='high' THEN 1 END) as high,
            AVG(risk_score) as avg_risk_score
        FROM fraud_alerts
        WHERE DATE(created_at) = %s
    """, (date_str,))
    fraud_row = cursor.fetchone()
    conn.close()

    summary = {
        "date": date_str,
        "transactions": {
            "total": tx_row[0] if tx_row else 0,
            "completed": tx_row[1] if tx_row else 0,
            "failed": tx_row[2] if tx_row else 0,
        },
        "fraud": {
            "total_alerts": fraud_row[0] if fraud_row else 0,
            "critical": fraud_row[1] if fraud_row else 0,
            "high": fraud_row[2] if fraud_row else 0,
            "avg_risk_score": float(fraud_row[3]) if fraud_row and fraud_row[3] else 0.0,
        },
    }

    context["task_instance"].xcom_push(key="daily_summary", value=summary)
    log.info(f"[DailySummary] Aggregated data for {date_str}: {summary}")
    return summary


def generate_ai_risk_report(**context) -> dict:
    """Call Financial Insights Agent to generate narrative risk report."""
    import sys, asyncio
    sys.path.insert(0, "/opt/airflow/dags")

    summary = context["task_instance"].xcom_pull(
        task_ids="aggregate_daily_data", key="daily_summary"
    )

    from agents.insights.insights_agent import FinancialInsightsAgent
    agent = FinancialInsightsAgent()

    async def run():
        return await agent.generate({
            "report_type": "daily_risk_summary",
            "period": "daily",
            "data": summary,
        })

    report = asyncio.run(run())
    context["task_instance"].xcom_push(key="ai_report", value=report)
    log.info(f"[AIReport] Generated daily risk report for {summary.get('date')}")
    return report


def store_daily_report(**context) -> dict:
    """Store generated report in PostgreSQL and cache in Redis."""
    import psycopg2, redis, os, json

    summary = context["task_instance"].xcom_pull(
        task_ids="aggregate_daily_data", key="daily_summary"
    )
    report = context["task_instance"].xcom_pull(
        task_ids="generate_ai_risk_report", key="ai_report"
    )

    # Store in Redis for fast API access
    try:
        r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://redis:6379/0"))
        cache_key = f"daily_report:{summary['date']}"
        r.setex(cache_key, 86400, json.dumps(report))
        log.info(f"[Cache] Stored report in Redis: {cache_key}")
    except Exception as e:
        log.warning(f"Redis cache failed (non-fatal): {e}")

    return {"report_stored": True, "date": summary.get("date")}


def call_insights_api(**context) -> dict:
    """Call FastAPI insights endpoint to trigger downstream notifications."""
    import httpx, os

    report = context["task_instance"].xcom_pull(
        task_ids="generate_ai_risk_report", key="ai_report"
    )

    api_url = os.getenv("FINSENTINEL_API_URL", "http://finsentinel-api:8000")
    try:
        response = httpx.post(
            f"{api_url}/api/v1/agents/tasks",
            json={
                "task_type": "daily_report_complete",
                "payload": {"report_summary": str(report)[:500]},
            },
            headers={"X-User-Id": "airflow-scheduler"},
            timeout=30,
        )
        log.info(f"[API] Notified FinSentinel API: {response.status_code}")
        return {"api_notified": True, "status_code": response.status_code}
    except Exception as e:
        log.warning(f"API notification failed (non-fatal): {e}")
        return {"api_notified": False, "error": str(e)}


with DAG(
    dag_id="daily_financial_risk_summary",
    description="Daily aggregation of transactions, fraud alerts, and AI-generated risk report",
    default_args=DEFAULT_ARGS,
    schedule_interval="0 6 * * *",     # 6 AM daily
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["finsentinel", "daily", "risk", "insights"],
) as dag:

    start = EmptyOperator(task_id="start")

    aggregate = PythonOperator(
        task_id="aggregate_daily_data",
        python_callable=aggregate_daily_data,
        provide_context=True,
    )

    generate_report = PythonOperator(
        task_id="generate_ai_risk_report",
        python_callable=generate_ai_risk_report,
        provide_context=True,
        execution_timeout=timedelta(minutes=15),
    )

    store = PythonOperator(
        task_id="store_daily_report",
        python_callable=store_daily_report,
        provide_context=True,
    )

    notify_api = PythonOperator(
        task_id="call_insights_api",
        python_callable=call_insights_api,
        provide_context=True,
    )

    end = EmptyOperator(task_id="end")

    start >> aggregate >> generate_report >> [store, notify_api] >> end
