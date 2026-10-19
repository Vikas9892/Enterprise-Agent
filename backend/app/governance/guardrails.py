"""Real-time PII masking, prompt injection detection, and content safety filters."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple


class PIIMasker:
    """Detects and redacts personally identifiable information (PII) to comply with GDPR/HIPAA."""

    # Pre-compiled regex patterns
    EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    # Matches common US and international phone numbers
    PHONE_REGEX = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
    # US Social Security Number: XXX-XX-XXXX
    SSN_REGEX = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    # Credit card numbers (Visa, MC, Amex, Discover 13-19 digits with dashes or spaces)
    CREDIT_CARD_REGEX = re.compile(
        r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12})\b"
        r"|\b(?:\d{4}[-\s]\d{4}[-\s]\d{4}[-\s]\d{4})\b"
    )
    # API key tokens / secrets
    API_KEY_REGEX = re.compile(r"\b(?:sk-[a-zA-Z0-9]{20,}|ea_live_[a-zA-Z0-9]{20,}|bearer\s+[a-zA-Z0-9_\-\.]{20,})\b", re.IGNORECASE)

    def mask(self, text: str) -> Tuple[str, Dict[str, int]]:
        """Redact sensitive patterns and return masked text along with tally of redacting events."""
        if not text:
            return "", {}

        tally: Dict[str, int] = {
            "credit_cards": 0,
            "ssns": 0,
            "emails": 0,
            "phones": 0,
            "api_keys": 0,
        }

        # 1. Credit Cards
        def replace_cc(m):
            tally["credit_cards"] += 1
            return "[REDACTED_CC]"
        masked = self.CREDIT_CARD_REGEX.sub(replace_cc, text)

        # 2. SSN
        def replace_ssn(m):
            tally["ssns"] += 1
            return "[REDACTED_SSN]"
        masked = self.SSN_REGEX.sub(replace_ssn, masked)

        # 3. API Keys
        def replace_key(m):
            tally["api_keys"] += 1
            return "[REDACTED_KEY]"
        masked = self.API_KEY_REGEX.sub(replace_key, masked)

        # 4. Emails
        def replace_email(m):
            tally["emails"] += 1
            return "[REDACTED_EMAIL]"
        masked = self.EMAIL_REGEX.sub(replace_email, masked)

        # 5. Phone numbers
        def replace_phone(m):
            tally["phones"] += 1
            return "[REDACTED_PHONE]"
        masked = self.PHONE_REGEX.sub(replace_phone, masked)

        # Remove zeroes
        final_tally = {k: v for k, v in tally.items() if v > 0}
        return masked, final_tally


class PromptInjectionDetector:
    """Identifies adversarial prompt injection attacks, jailbreak attempts, and system overrides."""

    ADVERSARIAL_PATTERNS = [
        re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
        re.compile(r"disregard\s+(all\s+)?(previous|prior)\s+instructions", re.IGNORECASE),
        re.compile(r"system\s+(override|prompt|bypass)", re.IGNORECASE),
        re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
        re.compile(r"dan\s+mode|jailbreak", re.IGNORECASE),
        re.compile(r"reveal\s+your\s+(system\s+prompt|secret\s+instructions)", re.IGNORECASE),
        re.compile(r"bypass\s+all\s+(filters|guardrails|safety)", re.IGNORECASE),
        re.compile(r"do\s+anything\s+now", re.IGNORECASE),
    ]

    def inspect(self, prompt: str) -> Dict[str, Any]:
        """Assess prompt for injection risk. Returns is_suspicious, confidence, and matched patterns."""
        if not prompt:
            return {"is_suspicious": False, "confidence": 0.0, "matched_patterns": []}

        matched: List[str] = []
        for pat in self.ADVERSARIAL_PATTERNS:
            found = pat.search(prompt)
            if found:
                matched.append(found.group(0))

        is_suspicious = len(matched) > 0
        confidence = min(1.0, 0.4 + (len(matched) * 0.3)) if is_suspicious else 0.0

        return {
            "is_suspicious": is_suspicious,
            "confidence": round(confidence, 2),
            "matched_patterns": matched,
            "threat_level": "high" if len(matched) >= 2 else ("medium" if is_suspicious else "low"),
        }


class HarmfulContentFilter:
    """Heuristic safety filter flagging malware, exploits, and harmful operational instructions."""

    HARMFUL_TERMS = {
        "drop database", "drop table", "truncate table", "rm -rf /", ":(){ :|:& };:",
        "format c:", "delete from users", "cat /etc/shadow"
    }

    def check(self, text: str) -> Dict[str, Any]:
        lower = text.lower()
        flagged = [t for t in self.HARMFUL_TERMS if t in lower]
        return {
            "is_safe": len(flagged) == 0,
            "flagged_terms": flagged,
        }
