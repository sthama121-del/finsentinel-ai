# FinSentinel AI

**Enterprise-Grade Agentic AI Platform for Banking & Financial Services**

> Multi-agent orchestration · LLM-agnostic · Local-first with Ollama · Event-driven · Production-ready

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Tech Stack & Why Each Was Chosen](#3-tech-stack--why-each-was-chosen)
4. [LLM Provider-Agnostic Design](#4-llm-provider-agnostic-design)
5. [Why Local-First with Ollama](#5-why-local-first-with-ollama)
6. [Multi-Agent Design](#6-multi-agent-design)
7. [Setup — Local (Ollama)](#7-setup--local-ollama)
8. [Setup — Cloud (Azure)](#8-setup--cloud-azure)
9. [Switching LLM Providers](#9-switching-llm-providers)
10. [Sample API Usage](#10-sample-api-usage)
11. [Demo Scenarios](#11-demo-scenarios)
12. [Security & Governance](#12-security--governance)
13. [Monitoring & Evaluation](#13-monitoring--evaluation)
14. [Production Considerations](#14-production-considerations)
15. [Future Enhancements](#15-future-enhancements)
16. [Project Structure](#16-project-structure)

---

## 1. Project Overview

**FinSentinel AI** is a production-grade, event-driven AI platform built for the Banking and Financial Services (BFSI) industry. It enables intelligent automation of core financial workflows through a multi-agent AI architecture that is fully provider-agnostic — meaning it runs locally via Ollama (free, offline, CPU-based) or connects to OpenAI, Anthropic, or Azure OpenAI with a single configuration change.

### What It Does

| Capability | Description |
|---|---|
| **Fraud Detection** | Real-time transaction risk scoring using AI + rule engine |
| **Transaction Analysis** | Automatic categorization, enrichment, and anomaly flagging |
| **Customer Service** | RAG-powered conversational AI for banking queries |
| **Financial Insights** | AI-generated spend reports, trend analysis, cash flow forecasting |
| **Human-in-the-Loop** | Approval workflows for high-risk AI decisions |
| **Compliance** | PII masking, audit trails, RBAC, regulatory-ready design |

### Key Design Decisions

- **Local-first**: Full system runs on a developer laptop (AMD Ryzen 7, 32GB RAM) with no paid APIs
- **Provider-agnostic**: Switch LLMs via one environment variable
- **Event-driven**: Kafka-based real-time pipeline for streaming financial events
- **Microservice-ready**: FastAPI services with Docker Compose locally, Kubernetes on Azure

---

## 2. Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FinSentinel AI Platform                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────┐    ┌─────────────────────────────────────────┐    │
│  │  API Layer   │    │         Agentic Layer                    │    │
│  │  FastAPI     │───▶│  Orchestrator Agent                      │    │
│  │  REST/gRPC   │    │  ├── Fraud Detection Agent               │    │
│  │  JWT + RBAC  │    │  ├── Transaction Analysis Agent          │    │
│  └──────────────┘    │  ├── Customer Service Agent              │    │
│                       │  ├── Financial Insights Agent            │    │
│  ┌──────────────┐    │  └── Compliance Agent                   │    │
│  │ Event Stream │    └─────────────────┬───────────────────────┘    │
│  │   Kafka      │                      │                             │
│  │ Transactions │          ┌───────────▼────────────┐              │
│  │ Alerts       │          │   LLM Provider Layer    │              │
│  │ Audit Logs   │          │  ┌──────────────────┐  │              │
│  └──────────────┘          │  │ Ollama (default)  │  │              │
│                             │  │ OpenAI (optional) │  │              │
│  ┌──────────────┐          │  │ Anthropic (opt.)  │  │              │
│  │  RAG Layer   │          │  │ Azure OpenAI (opt)│  │              │
│  │  ChromaDB    │◀─────────│  └──────────────────┘  │              │
│  │  Embeddings  │          └────────────────────────┘              │
│  │  Retrieval   │                                                    │
│  └──────────────┘    ┌─────────────────────────────────────────┐   │
│                       │         Storage Layer                     │   │
│  ┌──────────────┐    │  PostgreSQL │ Redis │ ChromaDB            │   │
│  │  Security    │    │  Azure ADLS Gen2 (cloud)                  │   │
│  │  PII Masking │    └─────────────────────────────────────────┘   │
│  │  Audit Logs  │                                                    │
│  │  RBAC + JWT  │    ┌─────────────────────────────────────────┐   │
│  └──────────────┘    │      Observability                        │   │
│                       │  Prometheus │ Grafana │ OpenTelemetry     │   │
│                       └─────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
Financial Event (Transaction)
        │
        ▼
[Kafka: fin.transactions.raw]
        │
        ▼
[Kafka Consumer] → PII Redactor → Orchestrator Agent
                                         │
                            ┌────────────▼───────────┐
                            │  Route to Agent         │
                            │  (LLM reasoning)        │
                            └────────────┬───────────┘
                                         │
                          ┌──────────────▼──────────────┐
                          │  Specialist Agent            │
                          │  + RAG Context Retrieval     │
                          │  + LLM (Ollama/Cloud)        │
                          └──────────────┬──────────────┘
                                         │
                          ┌──────────────▼──────────────┐
                          │  Result + Audit Log          │
                          │  High Risk → Human Approval  │
                          │  Alert → Kafka fin.alerts    │
                          └─────────────────────────────┘
```

---

## 3. Tech Stack & Why Each Was Chosen

### Core Framework

| Component | Technology | Why |
|---|---|---|
| **API Framework** | FastAPI | Async-native, auto-docs (OpenAPI), Pydantic validation, production-proven |
| **LLM Orchestration** | LangChain | Provider-agnostic, rich ecosystem, ReAct agent framework |
| **Local LLM** | Ollama | Free, offline, CPU-compatible, runs mistral:7b on 32GB RAM |
| **Vector Store** | ChromaDB (local) / Qdrant | Persistent, fast, open-source, swappable for Azure AI Search |
| **Event Streaming** | Apache Kafka | Industry standard for financial event streaming, durable, replay-capable |
| **Primary Database** | PostgreSQL | ACID compliance critical for financial data, mature ecosystem |
| **Cache** | Redis | Sub-millisecond LLM response caching, session management |
| **Containerization** | Docker + Kubernetes | Local dev → AKS cloud deployment without changes |

### Azure Cloud Mapping

| Local / AWS Component | Azure Equivalent | Purpose |
|---|---|---|
| Ollama (local) | Azure OpenAI Service | LLM inference |
| ChromaDB / Qdrant | Azure AI Search | Vector search at scale |
| Kafka (Docker) | Azure Event Hubs | Event streaming (Kafka-compatible API) |
| PostgreSQL (Docker) | Azure Database for PostgreSQL Flexible | Managed relational DB |
| Redis (Docker) | Azure Cache for Redis | Managed caching |
| Local filesystem | Azure Data Lake Storage Gen2 | Document and data storage |
| Docker Compose | Azure Kubernetes Service (AKS) | Container orchestration |
| Local secrets (.env) | Azure Key Vault | Secret management |
| Grafana/Prometheus | Azure Monitor + Application Insights | Observability |
| Self-managed auth | Azure Active Directory (Entra ID) | Enterprise identity |

---

## 4. LLM Provider-Agnostic Design

FinSentinel AI uses the **Factory Pattern** to decouple all application logic from any specific LLM provider. Every agent, RAG pipeline, and workflow interacts only with the `BaseLLMProvider` abstraction.

### How It Works

```python
# config/.env — the ONLY place you change to switch providers
LLM_PROVIDER=ollama          # local, free
# LLM_PROVIDER=openai        # cloud
# LLM_PROVIDER=anthropic     # cloud
# LLM_PROVIDER=azure_openai  # enterprise cloud
```

```python
# Every agent uses this — never instantiates a provider directly
from llm.providers.factory import get_llm_provider

provider = get_llm_provider()       # reads LLM_PROVIDER from env
llm = provider.get_chat_model()     # returns LangChain-compatible model
embedder = provider.get_embedding_model()
```

### Provider Registry

```
llm/providers/factory.py
├── BaseLLMProvider (abstract)
├── OllamaProvider      → langchain_ollama.ChatOllama
├── OpenAIProvider      → langchain_openai.ChatOpenAI
├── AnthropicProvider   → langchain_anthropic.ChatAnthropic
└── AzureOpenAIProvider → langchain_openai.AzureChatOpenAI
```

Adding a new provider (e.g., Google Gemini) requires only:
1. Creating a new class inheriting `BaseLLMProvider`
2. Registering it in `_PROVIDER_REGISTRY`
3. Zero changes to agents or business logic

---

## 5. Why Local-First with Ollama

| Concern | Ollama Solution |
|---|---|
| **Cost** | Zero API costs during development and testing |
| **Data Privacy** | Sensitive financial data never leaves your machine |
| **Internet dependency** | Works fully offline — no rate limits, no downtime |
| **Compliance** | Financial orgs often can't send data to external APIs in dev |
| **Speed to start** | No account signup, API key setup, or billing configuration |

### Models Selected for Your Machine (AMD Ryzen 7 8700G, 32GB RAM)

| Model | Size | Use Case | RAM Usage |
|---|---|---|---|
| `mistral:7b-instruct` | 4.1 GB | Main LLM (agents, reasoning) | ~8 GB |
| `nomic-embed-text` | 274 MB | Document embeddings (RAG) | ~1 GB |

These models run fully on CPU. With 32GB RAM you have comfortable headroom.

---

## 6. Multi-Agent Design

### Orchestrator Agent

**Role**: Master controller. Receives all tasks, reasons about routing using LLM, delegates to specialist agents, manages retries, human approvals, and audit logging.

**Tools**: Task queue, retry logic, audit logger, PII redactor, approval workflow

### Fraud Detection Agent

**Role**: Analyzes every transaction for fraud patterns in real time.

**Tools**: LLM risk reasoning, velocity checker, geo-anomaly detector, rule engine

**Output**: `risk_score` (0-100), `risk_level`, `recommended_action`, `fraud_patterns`

### Transaction Analysis Agent

**Role**: Enriches and categorizes transactions for reporting and UX.

**Tools**: LLM categorization, merchant lookup, spend pattern analyzer

**Output**: Category, subcategory, recurring flag, tax deductibility, tags

### Customer Service Agent

**Role**: Answers customer banking queries using the policy knowledge base.

**Tools**: RAG retrieval (policy docs), conversation history, escalation detector

**Output**: Natural language response, escalation flag

### Financial Insights Agent

**Role**: Generates spend summaries, trend reports, and financial health assessments.

**Tools**: LLM analytics, spend aggregator, cash flow modeler

**Output**: Structured JSON reports with metrics, insights, and recommendations

### Human-in-the-Loop Workflow

Tasks are automatically flagged for human approval when:
- Transaction amount exceeds $50,000
- Task type is `block_account`, `approve_loan`, or `aml_flag`
- Fraud risk score exceeds 80 (configurable)

Flagged tasks enter `AWAITING_APPROVAL` state until a human approver calls the `/approve` endpoint.

---

## 7. Setup — Local (Ollama)

### Prerequisites

| Tool | Version | Download |
|---|---|---|
| Python | 3.11+ | python.org |
| Docker Desktop | Latest | docker.com |
| Ollama | Latest | ollama.ai |
| VS Code | Latest | code.visualstudio.com |
| Git | Latest | git-scm.com |

### Step-by-Step Setup

#### Option A: Automated (Recommended for Windows)

```batch
REM Clone the repo
git clone https://github.com/sthama121-del/finsentinel-ai.git
cd finsentinel-ai

REM Run the setup script (handles everything)
setup.bat
```

#### Option B: Manual

**Step 1 — Clone and configure**

```batch
cd C:\Users\srikr\Documents\github
git clone https://github.com/sthama121-del/finsentinel-ai.git
cd finsentinel-ai
copy .env.example .env
```

**Step 2 — Create virtual environment**

```batch
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**Step 3 — Pull Ollama models**

```batch
REM Pull the main LLM (~4.1 GB, one-time download)
ollama pull mistral:7b-instruct

REM Pull the embedding model (~274 MB)
ollama pull nomic-embed-text

REM Verify Ollama is running
ollama list
```

**Step 4 — Start infrastructure**

```batch
REM Start all services (PostgreSQL, Redis, Kafka, ChromaDB, Prometheus, Grafana)
docker-compose up -d

REM Wait ~30 seconds, then verify
docker-compose ps
```

**Step 5 — Start the API server**

```batch
python main.py
```

**Step 6 — Verify everything works**

```batch
python test_quick.py
```

### Service URLs After Setup

| Service | URL | Credentials |
|---|---|---|
| **FinSentinel API** | http://localhost:8000 | — |
| **API Documentation** | http://localhost:8000/api/docs | — |
| **Kafka UI** | http://localhost:8080 | — |
| **Grafana** | http://localhost:3000 | admin / finsentinel |
| **Prometheus** | http://localhost:9090 | — |
| **ChromaDB** | http://localhost:8001 | — |

---

## 8. Setup — Cloud (Azure)

### Prerequisites

- Azure CLI installed and logged in: `az login`
- Azure subscription with contributor access
- Docker image pushed to Azure Container Registry (ACR)

### Azure Resource Setup

```bash
# Set variables
RESOURCE_GROUP=finsentinel-rg
LOCATION=eastus
AKS_NAME=finsentinel-aks
ACR_NAME=finsentinelacr

# Create Resource Group
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Azure Container Registry
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Standard

# Create AKS cluster
az aks create \
  --resource-group $RESOURCE_GROUP \
  --name $AKS_NAME \
  --node-count 3 \
  --node-vm-size Standard_D4s_v3 \
  --enable-managed-identity \
  --attach-acr $ACR_NAME \
  --generate-ssh-keys

# Get credentials
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_NAME
```

### Build and Push Docker Image

```bash
# Build image
docker build -t finsentinel-ai:1.0.0 -f docker/Dockerfile .

# Tag and push to ACR
az acr login --name $ACR_NAME
docker tag finsentinel-ai:1.0.0 $ACR_NAME.azurecr.io/finsentinel-ai:1.0.0
docker push $ACR_NAME.azurecr.io/finsentinel-ai:1.0.0
```

### Deploy to AKS

```bash
# Update image reference in deployment.yaml, then:
kubectl apply -f infrastructure/k8s/deployment.yaml

# Verify deployment
kubectl get pods -n finsentinel
kubectl get services -n finsentinel
```

### Azure OpenAI Setup

```bash
# Create Azure OpenAI resource
az cognitiveservices account create \
  --name finsentinel-openai \
  --resource-group $RESOURCE_GROUP \
  --kind OpenAI \
  --sku S0 \
  --location eastus

# Deploy GPT-4o model
az cognitiveservices account deployment create \
  --name finsentinel-openai \
  --resource-group $RESOURCE_GROUP \
  --deployment-name gpt-4o \
  --model-name gpt-4o \
  --model-version "2024-05-13" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name Standard
```

Then update `.env`:

```env
LLM_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://finsentinel-openai.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
```

---

## 9. Switching LLM Providers

The **only file you ever change** is `.env`. No code modifications required.

### Local (Default)

```env
LLM_PROVIDER=ollama
LLM_MODEL=mistral:7b-instruct
OLLAMA_BASE_URL=http://localhost:11434
```

### OpenAI

```env
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
OPENAI_API_KEY=sk-your-key-here
```

### Anthropic

```env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Azure OpenAI (Production)

```env
LLM_PROVIDER=azure_openai
LLM_MODEL=gpt-4o
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-15-preview
```

After changing `.env`, restart the API server. No other changes needed.

---

## 10. Sample API Usage

### Get an Auth Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "analyst@finsentinel.com", "password": "demo123"}'
```

### Analyze a Transaction for Fraud

```bash
curl -X POST http://localhost:8000/api/v1/agents/fraud/analyze \
  -H "Content-Type: application/json" \
  -H "X-User-Id: analyst@finsentinel.com" \
  -d '{
    "transaction_id": "TXN-9A3F2B",
    "customer_id": "CUST-44120",
    "amount": 12500.00,
    "currency": "USD",
    "merchant": {
      "name": "Unknown Wire Transfer",
      "category": "Transfer",
      "country": "NG"
    },
    "card": {"type": "Visa", "last_four": "4242", "present": false},
    "velocity_last_24h": 15,
    "ip_country": "RU"
  }'
```

**Response:**

```json
{
  "risk_score": 87,
  "risk_level": "critical",
  "recommended_action": "block",
  "fraud_patterns": ["geo_anomaly", "velocity_anomaly", "card_not_present"],
  "confidence": 0.91,
  "reasoning": "Transaction flagged for multiple high-risk signals...",
  "flags": {
    "velocity_anomaly": true,
    "geo_anomaly": true,
    "amount_anomaly": true,
    "device_anomaly": false
  }
}
```

### Submit a Financial Insights Task

```bash
curl -X POST http://localhost:8000/api/v1/agents/tasks \
  -H "Content-Type: application/json" \
  -H "X-User-Id: analyst@finsentinel.com" \
  -d '{
    "task_type": "financial_insights",
    "payload": {
      "report_type": "spend_summary",
      "period": "monthly",
      "data": {
        "total_transactions": 87,
        "total_spend": 4250.00,
        "categories": {"Food": 820, "Travel": 1200, "Shopping": 630}
      }
    }
  }'
```

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

### Approve a High-Risk Task (Human-in-the-Loop)

```bash
# First, get the task_id from the submission response
curl -X POST http://localhost:8000/api/v1/agents/tasks/TASK-ID-HERE/approve \
  -H "Content-Type: application/json" \
  -d '{"approver_id": "admin@finsentinel.com"}'
```

---

## 11. Demo Scenarios

### Scenario 1: Real-Time Fraud Alert

A customer's card is used for a $15,500 purchase at a crypto exchange in Nigeria, while the customer is physically in Texas. The system:

1. Kafka consumer ingests the transaction event
2. Orchestrator routes to Fraud Detection Agent
3. Agent scores risk at 89/100 (critical)
4. Transaction is blocked automatically
5. Alert published to `fin.alerts` Kafka topic
6. Fraud team notified via audit log
7. Complete audit trail written to PostgreSQL

### Scenario 2: Customer Query via Conversational AI

Customer asks: *"Why was I charged a $35 overdraft fee last Tuesday?"*

1. Request hits Customer Service Agent
2. Agent retrieves overdraft policy from RAG knowledge base
3. Agent cross-references transaction context from payload
4. Generates personalized, policy-accurate response
5. If customer says "this is unacceptable," escalation flag triggers human handoff

### Scenario 3: Monthly Spend Intelligence Report

Finance analyst triggers a monthly report generation:

1. Task submitted to Financial Insights Agent
2. Agent analyzes 3 months of transaction data
3. Generates: spend breakdown, top categories, month-over-month trends, savings recommendations
4. Report available as structured JSON via API
5. Cached in Redis for 1 hour to serve subsequent requests

### Scenario 4: Large Wire Transfer — Human Approval Required

Operations submits a $75,000 international wire transfer task:

1. Orchestrator detects amount > $50,000
2. Task automatically enters `AWAITING_APPROVAL` state
3. Compliance officer receives notification
4. Officer reviews audit trail and AI risk assessment
5. Officer calls `/approve` endpoint with their ID
6. Task executes; full approval chain logged to audit table

### Scenario 5: Document Ingestion → Policy Knowledge Update

Compliance team uploads updated AML policy PDF:

1. POST to `/api/v1/rag/ingest` with the PDF
2. Document chunked into 512-token segments with 100-token overlap
3. Each chunk embedded using `nomic-embed-text` via Ollama
4. Embeddings stored in ChromaDB with metadata (source, date, department)
5. Customer Service Agent immediately uses updated policy in responses

---

## 12. Security & Governance

### PII Masking

All data is run through `PIIRedactor` before reaching the LLM:

- SSN patterns redacted: `***-**-****`
- Credit card numbers masked: `**** **** **** ****`
- Email addresses redacted: `***@***.***`
- Phone numbers masked: `***-***-****`
- Named fields (`customer_name`, `dob`, `address`) replaced with `[REDACTED]`

### Role-Based Access Control (RBAC)

| Role | Capabilities |
|---|---|
| `analyst` | Submit tasks, view results, query RAG |
| `admin` | All analyst permissions + approve tasks, manage users |
| `auditor` | Read-only access to all audit logs and task history |

### Audit Trail

Every AI decision generates an immutable audit record containing:
- Unique audit ID + timestamp
- Task ID + task type
- User who submitted and (if applicable) approved
- Result summary
- Any errors or escalations

Audit records flow to:
1. Structured JSON logs (always)
2. PostgreSQL `audit_logs` table (persistent)
3. Kafka `fin.audit.logs` topic (streaming)

---

## 13. Monitoring & Evaluation

### LLM Evaluation Metrics

The `LLMEvaluator` class tracks:

| Metric | Description |
|---|---|
| **Latency (ms)** | End-to-end LLM response time |
| **Relevance Score** | How grounded the response is in provided context |
| **Hallucination Risk** | Presence of uncertainty markers in financial responses |
| **JSON Parse Success** | Whether structured output is valid JSON |
| **Token Usage** | Prompt + completion tokens per request |

### Grafana Dashboards

Pre-configured dashboards (import from `docker/grafana/dashboards/`):

- **Agent Performance**: Task throughput, success rate, latency per agent
- **Fraud Detection**: Risk score distribution, alert volume, false positive rate
- **LLM Health**: Provider latency, cache hit rate, token consumption
- **Infrastructure**: Kafka lag, Redis memory, PostgreSQL connections

### Prometheus Metrics

Exposed at `http://localhost:8002/metrics`:

```
finsentinel_tasks_total{status="completed"} 142
finsentinel_tasks_total{status="failed"} 3
finsentinel_fraud_risk_score_histogram_bucket{le="30"} 89
finsentinel_llm_latency_ms_histogram{provider="ollama"} ...
finsentinel_cache_hit_rate 0.73
```

---

## 14. Production Considerations

### Latency Optimization

| Strategy | Implementation |
|---|---|
| Redis caching | LLM responses cached by prompt hash (TTL: 1 hour) |
| Embedding cache | Frequently queried documents cached in Redis |
| Async processing | All agent calls are `async/await` — no thread blocking |
| Ollama model loading | Model stays warm in memory between requests |
| Connection pooling | SQLAlchemy async pool, Redis connection pool |

Expected latencies (Ollama on AMD Ryzen 7):
- Health check: < 10ms
- Fraud analysis: 15–45 seconds (first call), 5–15s (warm model)
- Cache hit: < 50ms

On Azure OpenAI (GPT-4o): Fraud analysis < 3 seconds

### Failure Modes & Recovery

| Failure | Recovery Strategy |
|---|---|
| LLM timeout | Retry with exponential backoff (max 3 attempts) |
| Kafka consumer crash | Auto-restart via Docker `restart: unless-stopped` |
| Agent exception | Task escalated to `ESCALATED` state, human notified |
| DB connection loss | SQLAlchemy connection pool auto-reconnects |
| Bad JSON from LLM | Regex fallback extraction + graceful degradation |

### Scaling Strategy

**Local/Dev**: Single-process, 2 API workers
**Production (AKS)**:
- API: 2–10 replicas (HPA on CPU 70%)
- Consumer: 1 replica per Kafka partition (3 default)
- ChromaDB → Azure AI Search (managed, elastic)
- Redis → Azure Cache for Redis (Premium, clustering)
- PostgreSQL → Azure PostgreSQL Flexible (auto-scale storage)

### Cost Optimization (Cloud)

- Use Ollama for dev/test (zero cost)
- Enable Azure OpenAI PTU (provisioned throughput) for predictable production costs
- Redis caching reduces LLM API calls by 60–80% for repeated queries
- Kafka retention set to 7 days (not forever) to control storage costs

---

## 15. Future Enhancements

| Enhancement | Description | Priority |
|---|---|---|
| **LangGraph Integration** | Stateful, cyclic multi-agent workflows with graph-based orchestration | High |
| **Fine-tuned Models** | Domain-specific Mistral fine-tuned on financial datasets | High |
| **Streaming Responses** | Server-Sent Events (SSE) for real-time LLM output streaming | Medium |
| **Voice Interface** | Speech-to-text customer service channel via Whisper | Medium |
| **Model Router** | Automatic routing to cheapest/fastest model based on task complexity | Medium |
| **Synthetic Data** | Privacy-preserving synthetic transaction generation for model training | Medium |
| **LangSmith Integration** | Full LLM observability, evaluation, and prompt management | Low |
| **OpenFGA Authorization** | Fine-grained authorization model (Zanzibar-based) | Low |
| **Feature Store** | Real-time ML features for fraud model (Feast/Azure ML) | Low |
| **MCP Server** | Expose FinSentinel tools via Model Context Protocol | Future |

---

## 16. Project Structure

```
C:\Users\srikr\Documents\github\finsentinel-ai\
│
├── main.py                          # FastAPI app entry point
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment template (copy to .env)
├── .env                             # Your local config (gitignored)
├── setup.bat                        # Windows automated setup script
├── test_quick.py                    # Integration test suite
├── docker-compose.yml               # Full local stack
│
├── config/
│   └── settings.py                  # Pydantic settings (all config in one place)
│
├── llm/
│   └── providers/
│       └── factory.py               # LLM provider factory (Ollama/OpenAI/Anthropic/Azure)
│
├── agents/
│   ├── orchestrator/
│   │   └── orchestrator.py          # Master orchestrator — routes, retries, approvals
│   ├── fraud/
│   │   └── fraud_agent.py           # Fraud detection + risk scoring
│   ├── transaction/
│   │   └── transaction_agent.py     # Transaction categorization + enrichment
│   ├── customer/
│   │   └── customer_agent.py        # Conversational customer service
│   └── insights/
│       └── insights_agent.py        # Financial reports + trend analysis
│
├── api/
│   └── routes/
│       ├── agents.py                # Task submission, status, approval endpoints
│       ├── auth.py                  # JWT login endpoint
│       ├── health.py                # Health, readiness, liveness probes
│       └── rag.py                   # Document ingest + semantic search
│
├── rag/
│   └── pipeline.py                  # RAG pipeline (load → chunk → embed → retrieve)
│
├── pipeline/
│   └── streaming/
│       └── kafka_consumer.py        # Real-time Kafka transaction consumer
│
├── security/
│   ├── pii/
│   │   └── redactor.py              # PII masking before LLM processing
│   ├── audit/
│   │   └── logger.py                # Immutable audit trail
│   └── rbac/                        # Role-based access control (coming soon)
│
├── evaluation/
│   └── metrics/
│       └── llm_evaluator.py         # LLM accuracy, hallucination, latency scoring
│
├── data/
│   └── samples/
│       └── generator.py             # Synthetic transaction data generator
│
├── infrastructure/
│   ├── k8s/
│   │   └── deployment.yaml          # Kubernetes manifests (AKS-ready)
│   ├── terraform/                   # Azure infrastructure as code (coming soon)
│   └── azure/                       # Azure-specific configs
│
├── docker/
│   ├── Dockerfile                   # API image (multi-stage)
│   ├── Dockerfile.consumer          # Kafka consumer image
│   ├── postgres/
│   │   └── init.sql                 # DB schema + seed data
│   ├── prometheus/
│   │   └── prometheus.yml           # Scrape config
│   └── grafana/
│       └── dashboards/              # Pre-built Grafana dashboards
│
└── tests/
    ├── unit/                        # Unit tests per module
    ├── integration/                 # API integration tests
    └── e2e/                         # End-to-end scenario tests
```

---

## Author

**GitHub**: [sthama121-del](https://github.com/sthama121-del)

Built on: Windows 11 | AMD Ryzen 7 8700G | 32GB RAM | VS Code

---

*FinSentinel AI is designed for educational and demonstration purposes in the BFSI AI space. For production deployment in regulated financial environments, additional compliance, security hardening, and regulatory review are required.*
