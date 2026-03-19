@echo off
REM FinSentinel AI - Windows Local Setup Script
REM Machine: SriKrishna | AMD Ryzen 7 8700G | 32GB RAM
REM Run this from: C:\Users\srikr\Documents\github\finsentinel-ai

SETLOCAL EnableDelayedExpansion

echo.
echo ============================================================
echo  FinSentinel AI - Local Setup (Windows)
echo  AMD Ryzen 7 8700G ^| 32GB RAM ^| Ollama Local LLM
echo ============================================================
echo.

REM ─── Check prerequisites ──────────────────────────────────────────────────────
echo [1/7] Checking prerequisites...

where python >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Install Python 3.11+ from python.org
    pause & exit /b 1
)
python --version

where docker >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker Desktop not found. Install from docker.com
    pause & exit /b 1
)
docker --version

where ollama >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [WARN] Ollama not found. Downloading installer...
    echo Please install Ollama from: https://ollama.ai/download
    echo After install, re-run this script.
    start https://ollama.ai/download
    pause & exit /b 1
)
ollama --version

echo [OK] All prerequisites found.
echo.

REM ─── Copy .env ────────────────────────────────────────────────────────────────
echo [2/7] Setting up environment...
IF NOT EXIST .env (
    copy .env.example .env
    echo [OK] Created .env from .env.example
    echo [INFO] Edit .env to change LLM_PROVIDER if needed (default: ollama)
) ELSE (
    echo [SKIP] .env already exists
)
echo.

REM ─── Python Virtual Environment ───────────────────────────────────────────────
echo [3/7] Creating Python virtual environment...
IF NOT EXIST venv (
    python -m venv venv
    echo [OK] Virtual environment created
) ELSE (
    echo [SKIP] venv already exists
)

call venv\Scripts\activate.bat
echo [OK] Virtual environment activated

echo [3b/7] Installing Python dependencies (this may take 3-5 minutes)...
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
echo [OK] Dependencies installed
echo.

REM ─── Pull Ollama Models ───────────────────────────────────────────────────────
echo [4/7] Pulling Ollama models...
echo [INFO] This may take 10-20 minutes depending on your internet speed.
echo [INFO] Models are cached locally after first download.
echo.

echo Pulling mistral:7b-instruct (LLM - ~4.1GB)...
ollama pull mistral:7b-instruct

echo Pulling nomic-embed-text (Embeddings - ~274MB)...
ollama pull nomic-embed-text

echo [OK] Ollama models ready
echo.

REM ─── Start Docker Services ────────────────────────────────────────────────────
echo [5/7] Starting Docker infrastructure services...
echo [INFO] Starting: PostgreSQL, Redis, Kafka, ChromaDB, Prometheus, Grafana
docker-compose up -d postgres redis zookeeper kafka chroma prometheus grafana
echo.
echo [INFO] Waiting 30 seconds for services to initialize...
timeout /t 30 /nobreak >nul
echo [OK] Infrastructure services started
echo.

REM ─── Create Kafka Topics ─────────────────────────────────────────────────────
echo [6/7] Creating Kafka topics...
timeout /t 10 /nobreak >nul
docker exec finsentinel-kafka kafka-topics --create --if-not-exists ^
    --bootstrap-server localhost:9092 ^
    --topic fin.transactions.raw ^
    --partitions 3 --replication-factor 1 >nul 2>&1

docker exec finsentinel-kafka kafka-topics --create --if-not-exists ^
    --bootstrap-server localhost:9092 ^
    --topic fin.alerts ^
    --partitions 3 --replication-factor 1 >nul 2>&1

docker exec finsentinel-kafka kafka-topics --create --if-not-exists ^
    --bootstrap-server localhost:9092 ^
    --topic fin.audit.logs ^
    --partitions 1 --replication-factor 1 >nul 2>&1

echo [OK] Kafka topics created
echo.

REM ─── Summary ──────────────────────────────────────────────────────────────────
echo [7/7] Setup complete!
echo.
echo ============================================================
echo  SERVICE URLS
echo ============================================================
echo  API:          http://localhost:8000
echo  API Docs:     http://localhost:8000/api/docs
echo  Kafka UI:     http://localhost:8080
echo  Grafana:      http://localhost:3000  (admin / finsentinel)
echo  Prometheus:   http://localhost:9090
echo  ChromaDB:     http://localhost:8001
echo ============================================================
echo.
echo  TO START THE API SERVER:
echo    venv\Scripts\activate
echo    python main.py
echo.
echo  TO TEST FRAUD DETECTION:
echo    python data\samples\generator.py
echo.
echo  LLM Provider: ollama (mistral:7b-instruct) - LOCAL, FREE
echo  To switch providers: edit LLM_PROVIDER in .env
echo ============================================================

pause
