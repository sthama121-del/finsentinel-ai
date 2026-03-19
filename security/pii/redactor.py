"""
FinSentinel AI - PII Redactor
Masks personally identifiable information before LLM processing.
"""
import re
import copy
from typing import Any


class PIIRedactor:
    """
    Redacts PII from dictionaries and strings before passing to LLMs.
    Patterns: SSN, credit cards, email, phone, names in known fields.
    """

    PATTERNS = {
        "ssn": (r'\b\d{3}-\d{2}-\d{4}\b', "***-**-****"),
        "credit_card": (r'\b(?:\d[ -]?){13,19}\b', "**** **** **** ****"),
        "email": (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "***@***.***"),
        "phone": (r'\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b', "***-***-****"),
        "iban": (r'\b[A-Z]{2}\d{2}[A-Z0-9]{1,30}\b', "XX********************"),
    }

    PII_FIELD_NAMES = {
        "customer_name", "full_name", "first_name", "last_name",
        "email", "phone", "ssn", "tax_id", "dob", "date_of_birth",
        "address", "street", "zip_code", "passport_number",
    }

    def redact(self, data: Any) -> Any:
        if isinstance(data, dict):
            return {k: self._redact_field(k, v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.redact(item) for item in data]
        elif isinstance(data, str):
            return self._redact_string(data)
        return data

    def _redact_field(self, key: str, value: Any) -> Any:
        if key.lower() in self.PII_FIELD_NAMES:
            if isinstance(value, str) and len(value) > 0:
                return "[REDACTED]"
        return self.redact(value)

    def _redact_string(self, text: str) -> str:
        for _, (pattern, replacement) in self.PATTERNS.items():
            text = re.sub(pattern, replacement, text)
        return text
