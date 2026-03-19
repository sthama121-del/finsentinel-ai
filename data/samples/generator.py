"""
FinSentinel AI - Sample Data Generator
Generates realistic financial transaction data for local testing.
"""
import json
import random
import uuid
from datetime import datetime, timedelta
from typing import Generator


MERCHANTS = [
    ("Walmart Supercenter", "Retail", 5411),
    ("Shell Gas Station", "Fuel", 5541),
    ("McDonald's", "Restaurant", 5814),
    ("Delta Airlines", "Travel", 4511),
    ("Amazon.com", "Online Retail", 5999),
    ("CVS Pharmacy", "Healthcare", 5912),
    ("Starbucks", "Coffee", 5812),
    ("Chase ATM", "Cash", 6011),
    ("Netflix", "Streaming", 7841),
    ("Whole Foods Market", "Grocery", 5411),
]

SUSPICIOUS_MERCHANTS = [
    ("Crypto Exchange XYZ", "Crypto", 6051),
    ("International Wire", "Transfer", 6012),
    ("Unknown Merchant", "Unknown", 9999),
]

COUNTRIES = ["US", "US", "US", "US", "US", "GB", "CA", "MX", "NG", "CN", "RU"]
CARD_TYPES = ["Visa", "Mastercard", "Amex"]


def generate_transaction(
    make_suspicious: bool = False,
    customer_id: str | None = None,
) -> dict:
    """Generate a single realistic financial transaction."""
    cid = customer_id or f"CUST-{random.randint(10000, 99999)}"
    tx_id = f"TXN-{uuid.uuid4().hex[:12].upper()}"
    timestamp = datetime.utcnow() - timedelta(minutes=random.randint(0, 1440))

    if make_suspicious:
        merchant_name, merchant_type, mcc = random.choice(SUSPICIOUS_MERCHANTS)
        amount = round(random.uniform(5000, 150000), 2)
        country = random.choice(["NG", "RU", "CN"])
        velocity = random.randint(8, 25)
    else:
        merchant_name, merchant_type, mcc = random.choice(MERCHANTS)
        amount = round(random.uniform(5, 2500), 2)
        country = "US"
        velocity = random.randint(1, 5)

    return {
        "transaction_id": tx_id,
        "customer_id": cid,
        "timestamp": timestamp.isoformat(),
        "amount": amount,
        "currency": "USD",
        "merchant": {
            "name": merchant_name,
            "category": merchant_type,
            "mcc_code": mcc,
            "country": country,
        },
        "card": {
            "type": random.choice(CARD_TYPES),
            "last_four": str(random.randint(1000, 9999)),
            "present": not make_suspicious,
        },
        "channel": random.choice(["online", "in-store", "mobile"]),
        "ip_country": country if not make_suspicious else random.choice(["NG", "RU"]),
        "device_fingerprint": uuid.uuid4().hex,
        "velocity_last_24h": velocity,
        "account_age_days": random.randint(30, 3650),
        "metadata": {
            "test_data": True,
            "suspicious_flag": make_suspicious,
        },
    }


def generate_batch(
    count: int = 100,
    suspicious_ratio: float = 0.1,
) -> list[dict]:
    """Generate a batch of transactions with configurable suspicious ratio."""
    transactions = []
    for i in range(count):
        is_suspicious = random.random() < suspicious_ratio
        transactions.append(generate_transaction(make_suspicious=is_suspicious))
    return transactions


def generate_spend_data(months: int = 3) -> dict:
    """Generate spend summary data for insights agent testing."""
    categories = ["Food", "Travel", "Healthcare", "Shopping", "Utilities", "Entertainment"]
    monthly_data = []

    for m in range(months):
        month_date = datetime.utcnow() - timedelta(days=30 * m)
        monthly_data.append({
            "month": month_date.strftime("%Y-%m"),
            "total_spend": round(random.uniform(3000, 8000), 2),
            "categories": {
                cat: round(random.uniform(50, 2000), 2) for cat in categories
            },
            "transaction_count": random.randint(40, 120),
        })

    return {
        "customer_id": f"CUST-{random.randint(10000, 99999)}",
        "period_months": months,
        "data": monthly_data,
    }


if __name__ == "__main__":
    print("=== Sample Transactions ===")
    for tx in generate_batch(count=5, suspicious_ratio=0.4):
        print(json.dumps(tx, indent=2))
        print("---")

    print("\n=== Spend Data ===")
    print(json.dumps(generate_spend_data(months=3), indent=2))
