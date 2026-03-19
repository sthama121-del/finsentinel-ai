"""
FinSentinel AI - Quick Integration Test
Run this to verify the full stack is working locally.
Usage: python test_quick.py
"""
import asyncio
import sys
import httpx
import json

BASE_URL = "http://localhost:8000"


async def run_tests():
    print("\n" + "=" * 60)
    print("  FinSentinel AI - Quick Integration Test")
    print("=" * 60 + "\n")

    passed = 0
    failed = 0

    async with httpx.AsyncClient(timeout=120) as client:

        # ─── Test 1: Health Check ─────────────────────────────────────────────
        print("Test 1: Health Check...")
        try:
            r = await client.get(f"{BASE_URL}/api/v1/health")
            data = r.json()
            assert r.status_code == 200
            assert data["status"] == "healthy"
            print(f"  ✓ PASS | Provider: {data['llm_provider']} | Model: {data['llm_model']}")
            passed += 1
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            failed += 1

        # ─── Test 2: Auth Login ───────────────────────────────────────────────
        print("\nTest 2: Authentication...")
        token = None
        try:
            r = await client.post(f"{BASE_URL}/api/v1/auth/login", json={
                "email": "analyst@finsentinel.com",
                "password": "demo123"
            })
            data = r.json()
            assert r.status_code == 200
            assert "access_token" in data
            token = data["access_token"]
            print(f"  ✓ PASS | Role: {data['role']}")
            passed += 1
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            failed += 1

        headers = {"X-User-Id": "analyst@finsentinel.com"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # ─── Test 3: Fraud Detection ──────────────────────────────────────────
        print("\nTest 3: Fraud Detection (LLM call - may take 30-90s on Ollama)...")
        try:
            tx = {
                "transaction_id": "TXN-TEST-001",
                "customer_id": "CUST-12345",
                "amount": 15500.00,
                "currency": "USD",
                "merchant": {
                    "name": "Unknown Crypto Exchange",
                    "category": "Crypto",
                    "mcc_code": 6051,
                    "country": "NG",
                },
                "card": {"type": "Visa", "last_four": "4242", "present": False},
                "channel": "online",
                "velocity_last_24h": 12,
                "ip_country": "RU",
            }
            r = await client.post(
                f"{BASE_URL}/api/v1/agents/fraud/analyze",
                json=tx,
                headers=headers,
            )
            data = r.json()
            assert r.status_code == 200
            assert "risk_score" in data
            assert "recommended_action" in data
            print(f"  ✓ PASS | Risk Score: {data.get('risk_score')} | Action: {data.get('recommended_action')}")
            passed += 1
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            failed += 1

        # ─── Test 4: Task Submission ──────────────────────────────────────────
        print("\nTest 4: Agent Task Submission...")
        task_id = None
        try:
            r = await client.post(
                f"{BASE_URL}/api/v1/agents/tasks",
                json={
                    "task_type": "transaction_analysis",
                    "payload": {
                        "transaction_id": "TXN-TEST-002",
                        "amount": 89.99,
                        "merchant": {"name": "Starbucks", "category": "Coffee"},
                        "channel": "mobile",
                    }
                },
                headers=headers,
            )
            data = r.json()
            assert r.status_code == 200
            assert "task_id" in data
            task_id = data["task_id"]
            print(f"  ✓ PASS | Task ID: {task_id} | Status: {data['status']}")
            passed += 1
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            failed += 1

        # ─── Test 5: Task Status ──────────────────────────────────────────────
        if task_id:
            print("\nTest 5: Task Status Check...")
            try:
                await asyncio.sleep(2)
                r = await client.get(
                    f"{BASE_URL}/api/v1/agents/tasks/{task_id}",
                    headers=headers,
                )
                data = r.json()
                assert r.status_code == 200
                print(f"  ✓ PASS | Status: {data['status']}")
                passed += 1
            except Exception as e:
                print(f"  ✗ FAIL: {e}")
                failed += 1

        # ─── Test 6: RAG Endpoint ─────────────────────────────────────────────
        print("\nTest 6: RAG Query...")
        try:
            r = await client.post(
                f"{BASE_URL}/api/v1/rag/query",
                json={"query": "What is the fraud transaction limit policy?", "top_k": 3},
                headers=headers,
            )
            assert r.status_code == 200
            print(f"  ✓ PASS | RAG endpoint reachable")
            passed += 1
        except Exception as e:
            print(f"  ✗ FAIL: {e}")
            failed += 1

    # ─── Summary ─────────────────────────────────────────────────────────────
    total = passed + failed
    print("\n" + "=" * 60)
    print(f"  Results: {passed}/{total} tests passed")
    if failed > 0:
        print(f"  {failed} test(s) failed — check logs above")
    else:
        print("  All tests passed! FinSentinel AI is running correctly.")
    print("=" * 60 + "\n")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
