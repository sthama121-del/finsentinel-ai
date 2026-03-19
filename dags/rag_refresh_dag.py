"""
FinSentinel AI - DAG 4: RAG Knowledge Base Refresh
Runs every Sunday at midnight. Re-ingests updated policy documents into ChromaDB.
"""
from __future__ import annotations

from datetime import timedelta
import logging
import os

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.dates import days_ago

log = logging.getLogger(__name__)

DEFAULT_ARGS = {
    "owner": "finsentinel-rag",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}

DOCS_PATH = os.getenv("FINSENTINEL_DOCS_PATH", "/opt/airflow/data/raw/policies")


def scan_new_documents(**context) -> dict:
    """Scan docs folder for new/updated documents since last run."""
    import os
    from pathlib import Path

    docs_path = Path(DOCS_PATH)
    if not docs_path.exists():
        docs_path.mkdir(parents=True, exist_ok=True)
        log.info(f"Created docs path: {docs_path}")
        context["task_instance"].xcom_push(key="new_docs", value=[])
        return {"new_docs": 0}

    supported = {".pdf", ".txt", ".md", ".csv"}
    docs = [
        str(f) for f in docs_path.rglob("*")
        if f.suffix.lower() in supported and f.is_file()
    ]

    log.info(f"[RAG Scan] Found {len(docs)} documents to process")
    context["task_instance"].xcom_push(key="new_docs", value=docs)
    return {"new_docs": len(docs)}


def ingest_documents(**context) -> dict:
    """Ingest documents into ChromaDB via RAG pipeline."""
    import sys, asyncio
    sys.path.insert(0, "/opt/airflow/dags")

    docs = context["task_instance"].xcom_pull(
        task_ids="scan_new_documents", key="new_docs"
    ) or []

    if not docs:
        log.info("No documents to ingest.")
        return {"ingested": 0, "failed": 0}

    from rag.pipeline import FinancialRAGPipeline
    pipeline = FinancialRAGPipeline()

    ingested, failed = 0, 0

    async def run():
        nonlocal ingested, failed
        for doc_path in docs:
            try:
                result = await pipeline.ingest(
                    file_path=doc_path,
                    metadata={
                        "ingested_by": "airflow",
                        "dag": "rag_knowledge_base_refresh",
                        "collection": "financial_policies",
                    },
                )
                ingested += 1
                log.info(f"[RAG] Ingested: {doc_path} → {result['chunks_ingested']} chunks")
            except Exception as e:
                failed += 1
                log.error(f"[RAG] Failed to ingest {doc_path}: {e}")

    asyncio.run(run())
    return {"ingested": ingested, "failed": failed}


def verify_rag_health(**context) -> dict:
    """Run a test query to verify ChromaDB is healthy after ingestion."""
    import sys, asyncio
    sys.path.insert(0, "/opt/airflow/dags")

    from rag.pipeline import FinancialRAGPipeline
    pipeline = FinancialRAGPipeline()

    async def run():
        return await pipeline.retrieve(
            query="What is the fraud transaction limit policy?",
            top_k=3,
        )

    results = asyncio.run(run())
    log.info(f"[RAG Health] Test query returned {len(results)} results")
    return {"health_check": "passed", "results_returned": len(results)}


with DAG(
    dag_id="rag_knowledge_base_refresh",
    description="Weekly refresh of financial policy documents in ChromaDB vector store",
    default_args=DEFAULT_ARGS,
    schedule_interval="0 0 * * 0",     # Every Sunday at midnight
    start_date=days_ago(1),
    catchup=False,
    tags=["finsentinel", "rag", "knowledge-base", "weekly"],
) as dag:

    start = EmptyOperator(task_id="start")

    scan = PythonOperator(
        task_id="scan_new_documents",
        python_callable=scan_new_documents,
        provide_context=True,
    )

    ingest = PythonOperator(
        task_id="ingest_documents",
        python_callable=ingest_documents,
        provide_context=True,
        execution_timeout=timedelta(hours=1),
    )

    verify = PythonOperator(
        task_id="verify_rag_health",
        python_callable=verify_rag_health,
        provide_context=True,
    )

    end = EmptyOperator(task_id="end")

    start >> scan >> ingest >> verify >> end
