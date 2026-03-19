"""
FinSentinel AI - DAG 1: Transaction Ingestion & Enrichment Pipeline
Runs every 15 minutes. Pulls pending transactions, enriches via agent, stores results.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import json
import logging

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.dates import days_ago

log = logging.getLogger(__name__)

# ─── Default Args ─────────────────────────────────────────────────────────────
DEFAULT_ARGS = {
    "owner": "finsentinel",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "retry_exponential_backoff": True,
    "max_retry_delay": timedelta(minutes=10),
}


# ─── Task Functions ────────────────────────────────────────────────────────────

def extract_pending_transactions(**context) -> dict:
    """Pull unprocessed transactions from PostgreSQL."""
    import psycopg2
    import os

    conn = psycopg2.connect(os.getenv("POSTGRES_URL", "postgresql://finuser:finpass@postgres:5432/finsentinel"))
    cursor = conn.cursor()

    cursor.execute("""
        SELECT task_id, payload FROM agent_tasks
        WHERE task_type = 'transaction_analysis'
        AND status = 'pending'
        ORDER BY created_at ASC
        LIMIT 50
    """)
    rows = cursor.fetchall()
    conn.close()

    transactions = [{"task_id": r[0], "payload": r[1]} for r in rows]
    log.info(f"[Extract] Found {len(transactions)} pending transactions")

    context["task_instance"].xcom_push(key="transactions", value=transactions)
    return {"count": len(transactions)}


def enrich_transactions(**context) -> dict:
    """Call Transaction Analysis Agent for each transaction."""
    import sys
    sys.path.insert(0, "/opt/airflow/dags")

    transactions = context["task_instance"].xcom_pull(
        task_ids="extract_pending_transactions", key="transactions"
    )

    if not transactions:
        log.info("No transactions to enrich.")
        return {"enriched": 0}

    import asyncio
    from agents.transaction.transaction_agent import TransactionAnalysisAgent

    agent = TransactionAnalysisAgent()
    results = []

    async def run():
        for tx in transactions:
            try:
                result = await agent.analyze(tx["payload"])
                results.append({"task_id": tx["task_id"], "result": result, "status": "completed"})
            except Exception as e:
                log.error(f"Enrichment failed for {tx['task_id']}: {e}")
                results.append({"task_id": tx["task_id"], "error": str(e), "status": "failed"})

    asyncio.run(run())
    context["task_instance"].xcom_push(key="enriched_results", value=results)
    log.info(f"[Enrich] Processed {len(results)} transactions")
    return {"enriched": len(results)}


def store_enrichment_results(**context) -> dict:
    """Persist enriched results back to PostgreSQL."""
    import psycopg2
    import os
    import json

    results = context["task_instance"].xcom_pull(
        task_ids="enrich_transactions", key="enriched_results"
    )

    if not results:
        return {"stored": 0}

    conn = psycopg2.connect(os.getenv("POSTGRES_URL", "postgresql://finuser:finpass@postgres:5432/finsentinel"))
    cursor = conn.cursor()

    for r in results:
        cursor.execute("""
            UPDATE agent_tasks
            SET status = %s, result = %s, updated_at = NOW()
            WHERE task_id = %s
        """, (r["status"], json.dumps(r.get("result", {})), r["task_id"]))

    conn.commit()
    conn.close()

    log.info(f"[Store] Saved {len(results)} enrichment results")
    return {"stored": len(results)}


def publish_enrichment_events(**context) -> dict:
    """Publish enriched transaction events to Kafka."""
    from kafka import KafkaProducer
    import os
    import json

    results = context["task_instance"].xcom_pull(
        task_ids="enrich_transactions", key="enriched_results"
    )

    if not results:
        return {"published": 0}

    producer = KafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092"),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    count = 0
    for r in results:
        if r["status"] == "completed":
            producer.send("fin.transactions.enriched", r)
            count += 1

    producer.flush()
    producer.close()
    log.info(f"[Kafka] Published {count} enriched transaction events")
    return {"published": count}


def notify_on_failure(context):
    """Failure callback — logs to audit table."""
    log.error(
        f"[DAG FAILURE] DAG={context['dag'].dag_id} "
        f"Task={context['task'].task_id} "
        f"ExecutionDate={context['execution_date']}"
    )


# ─── DAG Definition ───────────────────────────────────────────────────────────
with DAG(
    dag_id="transaction_ingestion_enrichment",
    description="Ingest pending transactions, enrich via AI agent, store and publish results",
    default_args=DEFAULT_ARGS,
    schedule_interval="*/15 * * * *",   # Every 15 minutes
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=["finsentinel", "transactions", "enrichment"],
    on_failure_callback=notify_on_failure,
) as dag:

    start = EmptyOperator(task_id="start")

    extract = PythonOperator(
        task_id="extract_pending_transactions",
        python_callable=extract_pending_transactions,
        provide_context=True,
    )

    enrich = PythonOperator(
        task_id="enrich_transactions",
        python_callable=enrich_transactions,
        provide_context=True,
        execution_timeout=timedelta(minutes=10),
    )

    store = PythonOperator(
        task_id="store_enrichment_results",
        python_callable=store_enrichment_results,
        provide_context=True,
    )

    publish = PythonOperator(
        task_id="publish_enrichment_events",
        python_callable=publish_enrichment_events,
        provide_context=True,
    )

    end = EmptyOperator(task_id="end")

    # ─── Task Dependencies ─────────────────────────────────────────────────────
    start >> extract >> enrich >> [store, publish] >> end
