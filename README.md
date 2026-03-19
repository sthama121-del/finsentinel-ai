# FinSentinel AI

> **Production-grade Agentic AI Platform for Banking & Financial Services**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)](https://fastapi.tiangolo.com)
[![LangChain](https://img.shields.io/badge/LangChain-0.3-orange.svg)](https://langchain.com)
[![Airflow](https://img.shields.io/badge/Airflow-2.10.3-red.svg)](https://airflow.apache.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docker.com)
[![Ollama](https://img.shields.io/badge/LLM-Ollama%20Local-purple.svg)](https://ollama.ai)

---

## What Is This?

FinSentinel AI is a fully working, locally deployable AI platform that simulates real-world financial workflows using a multi-agent architecture. It demonstrates how modern AI engineering principles — agentic reasoning, RAG pipelines, event-driven design, and LLM abstraction — can be applied in a regulated financial services context.

The system runs 100% locally using Ollama (no cloud APIs, no cost) and can be switched to OpenAI, Anthropic, or Azure OpenAI with a single environment variable change.

---

## Key Capabilities

| Capability | Description |
|---|---|
| **Fraud Detection** | Real-time transaction risk scoring using local LLM reasoning |
| **Transaction Analysis** | AI-powered categorization, enrichment, and anomaly flagging |
| **Customer Service AI** | RAG-powered conversational assistant for banking queries |
| **Financial Insights** | Automated spend reports, trend analysis, cash flow summaries |
| **Human-in-the-Loop** | Approval workflows for high-risk AI decisions |
| **Airflow Orchestration** | Scheduled pipelines for batch processing and compliance |
| **Security & Governance** | PII masking, RBAC, immutable audit trails |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                      FinSentinel AI Platform                      │
│                                                                    │
│  ┌─────────────────┐   ┌────────────────────────────────────────┐ │
│  │   Airflow Layer  │   │           Agentic Layer                │ │
│  │   :8085          │   │                                        │ │
│  │  ┌────────────┐  │   │  Orchestrator Agent                    │ │
│  │  │ Scheduler  │──┼──▶│  ├── Fraud Detection Agent            │ │
│  │  │ Webserver  │  │   │  ├── Transaction Analysis Agent        │ │
│  │  └────────────┘  │   │  ├── Customer Service Agent            │ │
│  │                  │   │  ├── Financial Insights Agent          │ │
│  │  5 DAGs:         │   │  └── Compliance Agent                  │ │
│  │  • tx_ingest     │   └──────────────┬─────────────────────────┘ │
│  │  • fraud_detect  │                  │                            │
│  │  • daily_risk    │   ┌──────────────▼─────────────────────────┐ │
│  │  • rag_refresh   │   │         LLM Provider Layer              │ │
│  │  • audit_log     │   │  Ollama (default) │ OpenAI │ Anthropic  │ │
│  └─────────────────┘   │  Azure OpenAI     │ (config-based)      │ │
│                         └──────────────────────────────────────── ┘ │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────────────┐  │
│  │  FastAPI      │   │  RAG Layer   │   │  Event Streaming       │  │
│  │  REST API     │   │  ChromaDB    │   │  Kafka + Zookeeper     │  │
│  │  :8000        │   │  Embeddings  │   │  fin.transactions.raw  │  │
│  └──────────────┘   └──────────────┘   └────────────────────────┘  │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────────────┐  │
│  │  PostgreSQL   │   │  Redis       │   │  Observability         │  │
│  │  Audit + Data │   │  LLM Cache   │   │  Prometheus + Grafana  │  │
│  └──────────────┘   └──────────────┘   └────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Core Platform

| Component | Technology | Purpose |
|---|---|---|
| API Framework | FastAPI | Async REST API with auto-docs |
| LLM Orchestration | LangChain | Provider-agnostic agent framework |
| Local LLM | Ollama + Mistral 7B | Free, offline, CPU-compatible inference |
| Vector Store | ChromaDB | Document embeddings for RAG |
| Event Streaming | Apache Kafka | Real-time financial event pipeline |
| Orchestration | Apache Airflow | Scheduled batch pipelines |
| Primary Database | PostgreSQL | ACID-compliant financial data storage |
| Cache | Redis | LLM response caching, session store |
| Containerization | Docker Compose | Local full-stack deployment |

### Azure Cloud Mapping (Production)

| Local Component | Azure Equivalent |
|---|---|
| Ollama | Azure OpenAI Service |
| ChromaDB | Azure AI Search |
| Kafka | Azure Event Hubs |
| PostgreSQL | Azure Database for PostgreSQL Flexible |
| Redis | Azure Cache for Redis |
| Docker Compose | Azure Kubernetes Service (AKS) |
| Local Storage | Azure Data Lake Storage Gen2 |
| Grafana/Prometheus | Azure Monitor + Application Insights |

---

## LLM Provider-Agnostic Design

Every agent in FinSentinel AI uses an abstract `BaseLLMProvider` interface. The concrete provider is resolved at runtime from a single environment variable — no code changes required.

```
# .env — the ONLY file you change to switch providers
LLM_PROVIDER=ollama          # local, free, offline
LLM_PROVIDER=openai          # OpenAI GPT-4o
LLM_PROVIDER=anthropic       # Anthropic Claude
LLM_PROVIDER=azure_openai    # Azure OpenAI (production)
```

```python
# How every agent accesses the LLM — provider-agnostic
from llm.providers.factory import get_llm_provider

provider = get_llm_provider()        # reads LLM_PROVIDER from env
llm = provider.get_chat_model()      # LangChain-compatible model
embedder = get_embedding_model()     # embedding model
```

### Provider Registry

```
llm/providers/factory.py
├── BaseLLMProvider        (abstract interface)
├── OllamaProvider         → langchain_ollama.ChatOllama
├── OpenAIProvider         → langchain_openai.ChatOpenAI
├── AnthropicProvider      → langchain_anthropic.ChatAnthropic
└── AzureOpenAIProvider    → langchain_openai.AzureChatOpenAI
```

Adding a new provider requires only implementing `BaseLLMProvider` — zero changes to agents or business logic.

---

## Why Local-First with Ollama

| Concern | How Ollama Solves It |
|---|---|
| Cost | Zero API cost during development |
| Data Privacy | Sensitive financial data never leaves the machine |
| Compliance | No data sent to external services in development |
| Offline | Works without internet — no rate limits or downtime |
| Speed to start | No account setup, billing, or API key management |

### Models Used (Optimised for 32GB RAM)

| Model | Size | Purpose |
|---|---|---|
| `mistral:7b-instruct` | 4.1 GB | Main LLM for all agents |
| `nomic-embed-text` | 274 MB | Document embeddings for RAG |

---

## Multi-Agent Design

### Orchestrator Agent
Routes all tasks to specialist agents using LLM reasoning. Manages retries (exponential backoff), human approval workflows, and audit logging.

### Fraud Detection Agent
Scores every transaction 0–100 for fraud risk. Identifies velocity anomalies, geographic anomalies, card-not-present patterns, and amount anomalies. Returns structured JSON with reasoning.

### Transaction Analysis Agent
Categorises and enriches transactions with merchant type, recurring flag, tax deductibility assessment, and spend impact.

### Customer Service Agent
RAG-powered conversational assistant. Retrieves relevant policy documents from ChromaDB and generates grounded, policy-accurate responses.

### Financial Insights Agent
Generates structured spend summaries, month-over-month trends, savings recommendations, and risk flags from transaction data.

---

## Airflow DAG Pipelines

| DAG | Schedule | Purpose |
|---|---|---|
| `transaction_ingestion_enrichment` | Every 15 mins | Enrich pending transactions via AI agent |
| `fraud_detection_alert_pipeline` | Every 5 mins | Score transactions, generate fraud alerts |
| `daily_financial_risk_summary` | 6 AM daily | AI-generated daily risk report |
| `rag_knowledge_base_refresh` | Sunday midnight | Re-ingest updated policy documents |
| `audit_log_archival_compliance` | 1 AM daily | Archive logs, generate compliance summary |

### Airflow Integration Pattern

```
Airflow Scheduler
      │
      ▼
DAG Task (Python Operator)
      │
      ├── Direct Python call → AI Agent (for business logic)
      ├── FastAPI call       → /api/v1/agents/tasks (for notifications)
      └── Kafka publish      → fin.alerts (for event streaming)
```

---

## Prerequisites

| Tool | Version | Download |
|---|---|---|
| Python | 3.11+ | python.org |
| Docker Desktop | Latest | docker.com |
| Ollama | Latest | ollama.ai |
| Git | Latest | git-scm.com |
| VS Code | Latest | code.visualstudio.com |

> **Machine tested on:** Windows 11, AMD Ryzen 7 8700G, 32GB RAM

---

## Local Setup

### Step 1 — Clone and configure

```powershell
cd C:\Users\<yourname>\Documents\github
git clone https://github.com/sthama121-del/finsentinel-ai.git
cd finsentinel-ai
cp .env.example .env
```

### Step 2 — Create virtual environment

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3 — Pull Ollama models

```powershell
ollama pull mistral:7b-instruct
ollama pull nomic-embed-text
ollama list
```

### Step 4 — Start all Docker services

```powershell
docker compose up -d
```

> First run downloads ~3GB of Docker images. Takes 5–10 minutes.

### Step 5 — Verify all services are running

```powershell
docker compose ps
```

All containers should show `Up` or `Healthy`.

### Step 6 — Start the API server (if running outside Docker)

```powershell
python main.py
```

---

## Switching LLM Providers

Edit `.env` — one line change, no code modifications:

### Ollama (Local — Default)
```env
LLM_PROVIDER=ollama
LLM_MODEL=mistral:7b-instruct
```

### OpenAI
```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-your-key
```

### Anthropic
```env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-your-key
```

### Azure OpenAI
```env
LLM_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

Restart `python main.py` after changing `.env`.

---

## Service URLs

| Service | URL | Credentials |
|---|---|---|
| **API Docs** | http://localhost:8000/api/docs | — |
| **Airflow UI** | http://localhost:8085 | admin / finsentinel |
| **Grafana** | http://localhost:3000 | admin / finsentinel |
| **Kafka UI** | http://localhost:8080 | — |
| **Prometheus** | http://localhost:9090 | — |
| **ChromaDB** | http://localhost:8001 | — |

---

## API Usage Examples

### Authenticate

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "analyst@finsentinel.com", "password": "demo123"}'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "role": "analyst"
}
```

---

### Analyze a Transaction for Fraud

```bash
curl -X POST http://localhost:8000/api/v1/agents/fraud/analyze \
  -H "Content-Type: application/json" \
  -H "X-User-Id: analyst@finsentinel.com" \
  -d '{
    "transaction_id": "TXN-9A3F2B",
    "amount": 15500.00,
    "merchant": {
      "name": "Unknown Wire Transfer",
      "category": "Crypto",
      "country": "NG"
    },
    "card": {"type": "Visa", "last_four": "4242", "present": false},
    "velocity_last_24h": 12,
    "ip_country": "RU"
  }'
```

**Response:**
```json
{
  "risk_score": 85,
  "risk_level": "High",
  "recommended_action": "Block + escalate to fraud team",
  "confidence": 0.9,
  "fraud_patterns": ["velocity_anomaly", "geo_anomaly", "amount_anomaly"],
  "reasoning": "Transaction flagged for multiple high-risk signals...",
  "flags": {
    "velocity_anomaly": true,
    "geo_anomaly": true,
    "amount_anomaly": true,
    "device_anomaly": false
  }
}
```

---

### Submit a Task to the Orchestrator

```bash
curl -X POST http://localhost:8000/api/v1/agents/tasks \
  -H "Content-Type: application/json" \
  -H "X-User-Id: analyst@finsentinel.com" \
  -d '{
    "task_type": "financial_insights",
    "payload": {
      "report_type": "spend_summary",
      "period": "monthly",
      "data": {"total_spend": 4250.00, "transactions": 87}
    }
  }'
```

---

### Query the Knowledge Base (RAG)

```bash
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the maximum daily ATM withdrawal limit?",
    "collection": "financial_policies",
    "top_k": 5
  }'
```

---

### Approve a High-Risk Task (Human-in-the-Loop)

```bash
curl -X POST http://localhost:8000/api/v1/agents/tasks/{task_id}/approve \
  -H "Content-Type: application/json" \
  -d '{"approver_id": "admin@finsentinel.com"}'
```

---

## Security & Governance

### PII Masking
All data passes through `PIIRedactor` before reaching the LLM:
- SSN → `***-**-****`
- Credit cards → `**** **** **** ****`
- Email → `***@***.***`
- Named fields (customer_name, dob, address) → `[REDACTED]`

### Role-Based Access Control

| Role | Permissions |
|---|---|
| `analyst` | Submit tasks, view results, query RAG |
| `admin` | All analyst permissions + approve tasks |
| `auditor` | Read-only access to all audit logs |

### Audit Trail
Every AI decision generates an immutable record stored in PostgreSQL `audit_logs` table and published to Kafka `fin.audit.logs` topic.

---

## Monitoring & Evaluation

### Grafana Dashboards (http://localhost:3000)
- Agent task throughput and success rates
- Fraud alert volume and risk score distribution
- LLM latency and cache hit rates
- Infrastructure health

### LLM Evaluation Metrics
The `LLMEvaluator` class tracks:
- Response latency (ms)
- Relevance score (0.0–1.0)
- Hallucination risk (0.0–1.0)
- JSON parse success rate
- Token usage per request

---

## Production Considerations

### Latency

| Scenario | Latency |
|---|---|
| Ollama first call (cold start) | 20–60 seconds |
| Ollama warm model | 3–10 seconds |
| Redis cache hit | < 50ms |
| Azure OpenAI GPT-4o | ~2–4 seconds |

### Scaling Strategy
- **Local/Dev:** Single process, 2 API workers
- **Production (AKS):** 2–10 replicas with HPA on CPU 70%
- **Kafka:** 1 consumer replica per partition (3 default)
- **ChromaDB → Azure AI Search** for elastic vector search at scale

### Failure Recovery

| Failure | Recovery |
|---|---|
| LLM timeout | Retry with exponential backoff (max 3 attempts) |
| Kafka consumer crash | Auto-restart via Docker `restart: unless-stopped` |
| Bad JSON from LLM | Regex fallback extraction + graceful degradation |
| DB connection loss | SQLAlchemy async pool auto-reconnects |

---

## Project Structure

```
finsentinel-ai/
│
├── main.py                          # FastAPI application entry point
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment template
├── docker-compose.yml               # Full local stack (11 services)
├── .dockerignore                    # Docker build exclusions
│
├── config/
│   └── settings.py                  # Centralised Pydantic settings
│
├── llm/providers/
│   └── factory.py                   # LLM provider factory pattern
│
├── agents/
│   ├── orchestrator/orchestrator.py # Master orchestrator
│   ├── fraud/fraud_agent.py         # Fraud detection + risk scoring
│   ├── transaction/transaction_agent.py
│   ├── customer/customer_agent.py
│   └── insights/insights_agent.py
│
├── api/routes/
│   ├── agents.py                    # Task submission + approval endpoints
│   ├── auth.py                      # JWT authentication
│   ├── health.py                    # Health, readiness, liveness probes
│   └── rag.py                       # Document ingest + semantic search
│
├── dags/
│   ├── transaction_ingestion_dag.py
│   ├── fraud_detection_dag.py
│   ├── daily_risk_summary_dag.py
│   ├── rag_refresh_dag.py
│   └── audit_archival_dag.py
│
├── rag/pipeline.py                  # RAG pipeline (load → chunk → embed → retrieve)
├── pipeline/streaming/kafka_consumer.py
├── security/pii/redactor.py
├── security/audit/logger.py
├── evaluation/metrics/llm_evaluator.py
├── data/samples/generator.py
├── docker/Dockerfile
├── docker/postgres/init.sql
└── infrastructure/k8s/deployment.yaml
```

---

## Demo Accounts

| Email | Password | Role |
|---|---|---|
| analyst@finsentinel.com | demo123 | analyst |
| admin@finsentinel.com | admin123 | admin |
| auditor@finsentinel.com | audit123 | auditor |

---

## Future Enhancements

| Enhancement | Priority |
|---|---|
| LangGraph stateful multi-agent workflows | High |
| Fine-tuned Mistral on financial datasets | High |
| Streaming responses via Server-Sent Events | Medium |
| Azure Key Vault integration for secrets | Medium |
| OpenFGA fine-grained authorization | Low |
| MCP server to expose FinSentinel tools | Future |

---

## Author

**GitHub:** [sthama121-del](https://github.com/sthama121-del)

Built and tested on: Windows 11 · AMD Ryzen 7 8700G · 32GB RAM · VS Code

---

*FinSentinel AI is a demonstration platform for AI engineering in the BFSI domain. For regulated production deployment, additional compliance review and security hardening are required.*
