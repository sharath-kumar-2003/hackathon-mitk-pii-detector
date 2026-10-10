"""
AI-Powered PII Detector using Google Gemini API.

Uses Gemini's language understanding to detect PII entities in text
with high accuracy, including contextual and paraphrased PII that
regex-only systems miss.

Maintains the exact same public API as the previous detector so
gateway.py, tokenizer.py, and all consumers work without changes.
"""

import re
import os
import json
import time
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from google import genai
from google.genai import types


@dataclass
class PIISpan:
    """Lightweight span result compatible with the existing pipeline.

    Mimics the Presidio RecognizerResult interface so that gateway.py
    and tokenizer.py can consume these without any changes.
    """
    entity_type: str
    start: int
    end: int
    score: float


# System prompt for Gemini PII detection
PII_SYSTEM_PROMPT = """You are a PII (Personally Identifiable Information) detection engine.
Your task is to find ALL PII entities in the given text.

Detect these PII types:
- PERSON: Full names, first names, last names
- EMAIL_ADDRESS: Email addresses
- PHONE_NUMBER: Phone numbers (any format, including Indian +91)
- CREDIT_CARD: Credit card numbers, debit card numbers, ATM card numbers (15-19 digits, with or without spaces/dashes)
- CARD_PIN: ATM PIN, debit card PIN, credit card PIN, CVV / CVC numbers, OTPs, security passcodes (usually 3 to 6 digits)
- US_SSN: US Social Security Numbers (XXX-XX-XXXX)
- IN_AADHAAR: Indian Aadhaar numbers (12 digits, may have spaces)
- IN_PAN: Indian PAN card numbers (ABCDE1234F format)
- LOCATION: Cities, states, countries, addresses
- ORGANIZATION: Company names, institution names
- IP_ADDRESS: IP addresses
- URL: Web URLs
- DATE_OF_BIRTH: Dates that represent birthdays
- MEDICAL_LICENSE: Medical license numbers
- PASSPORT: Passport numbers
- DRIVER_LICENSE: Driver's license numbers
- BANK_ACCOUNT: Bank account numbers, IFSC codes, IBAN numbers
- SYNTHETIC_ID: Synthetic test IDs (SYNTH-ID-xxxx, AUTH-KEY-xxxx, USER-REF-xxxx)

Respond ONLY with a JSON array. Each element must have:
- "entity_type": one of the types above
- "value": the exact text substring (must be an exact match from the input)
- "score": confidence score between 0.0 and 1.0

If no PII is found, return an empty array: []

CRITICAL RULES:
- The "value" field MUST be an exact substring of the input text (character-for-character match)
- For PINs, ATM PINs, CVVs, and card numbers, capture the exact digits/number
- Do NOT paraphrase, reformat, or modify the value in any way
- Do NOT include any explanation, only the JSON array
- Be thorough — detect ALL instances of PII, even if there are many"""


ENTITY_TYPE_MAP = {
    "NAME": "PERSON",
    "PERSON": "PERSON",
    "PERSON_NAME": "PERSON",
    "FIRST_NAME": "PERSON",
    "LAST_NAME": "PERSON",
    "EMAIL": "EMAIL_ADDRESS",
    "EMAIL_ADDRESS": "EMAIL_ADDRESS",
    "PHONE": "PHONE_NUMBER",
    "PHONE_NUMBER": "PHONE_NUMBER",
    "MOBILE": "PHONE_NUMBER",
    "LANDLINE": "PHONE_NUMBER",
    "AADHAAR": "IN_AADHAAR",
    "AADHAAR_NUMBER": "IN_AADHAAR",
    "IN_AADHAAR": "IN_AADHAAR",
    "PAN": "IN_PAN",
    "PAN_NUMBER": "IN_PAN",
    "IN_PAN": "IN_PAN",
    "SSN": "US_SSN",
    "US_SSN": "US_SSN",
    "CREDIT_CARD": "CREDIT_CARD",
    "DEBIT_CARD": "CREDIT_CARD",
    "DEBIT_CARD_NUMBER": "CREDIT_CARD",
    "ATM_CARD": "CREDIT_CARD",
    "ATM_CARD_NUMBER": "CREDIT_CARD",
    "CARD_NUMBER": "CREDIT_CARD",
    "PAYMENT_CARD": "CREDIT_CARD",
    "ATM_PIN": "CARD_PIN",
    "CARD_PIN": "CARD_PIN",
    "DEBIT_PIN": "CARD_PIN",
    "DEBIT_CARD_PIN": "CARD_PIN",
    "PIN": "CARD_PIN",
    "PIN_NUMBER": "CARD_PIN",
    "CVV": "CARD_PIN",
    "CVV_NUMBER": "CARD_PIN",
    "CVC": "CARD_PIN",
    "OTP": "CARD_PIN",
    "PASSCODE": "CARD_PIN",
    "SECURITY_CODE": "CARD_PIN",
    "LOCATION": "LOCATION",
    "ADDRESS": "LOCATION",
    "CITY": "LOCATION",
    "ORGANIZATION": "ORGANIZATION",
    "COMPANY": "ORGANIZATION",
    "IP_ADDRESS": "IP_ADDRESS",
    "URL": "URL",
    "DATE_OF_BIRTH": "DATE_OF_BIRTH",
    "DOB": "DATE_OF_BIRTH",
    "PASSPORT": "PASSPORT",
    "PASSPORT_NUMBER": "PASSPORT",
    "DRIVER_LICENSE": "DRIVER_LICENSE",
    "DRIVERS_LICENSE": "DRIVER_LICENSE",
    "DRIVING_LICENSE": "DRIVER_LICENSE",
    "BANK_ACCOUNT": "BANK_ACCOUNT",
    "ACCOUNT_NUMBER": "BANK_ACCOUNT",
    "ROUTING_NUMBER": "BANK_ACCOUNT",
    "MEDICAL_LICENSE": "MEDICAL_LICENSE",
    "SYNTHETIC_ID": "SYNTHETIC_ID",
    "BIOMETRIC": "SYNTHETIC_ID",
    "BIOMETRIC_HASH": "SYNTHETIC_ID",
}


class PIIDetector:
    """AI-powered PII detector using Google Gemini API with regex augmentation."""

    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY", "")
        self.model_name = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
        # Quota tracking: timestamp when quota resets (None = not exhausted)
        self._quota_reset_at: Optional[float] = None
        self._quota_exhausted: bool = False

        if not api_key:
            print("[PIIDetector] WARNING: GEMINI_API_KEY not set. Will use regex-only detection.")
            print("[PIIDetector] Set GEMINI_API_KEY in your .env or environment variables.")
            self.client = None
        else:
            try:
                self.client = genai.Client(api_key=api_key)
                print(f"[PIIDetector] Google Gemini AI detector ({self.model_name}) initialized successfully.")
            except Exception as e:
                print(f"[PIIDetector] Failed to initialize Gemini client: {e}. Falling back to regex.")
                self.client = None

        # Regex patterns for structured PII (fast fallback + high precision augmentation)
        self.regex_patterns: List[Dict[str, Any]] = [
            {
                "entity_type": "US_SSN",
                "pattern": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
                "score": 0.99,
            },
            {
                "entity_type": "EMAIL_ADDRESS",
                "pattern": re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
                "score": 0.99,
            },
            {
                "entity_type": "IN_PAN",
                "pattern": re.compile(r"\b[A-Z]{5}\d{4}[A-Z]{1}\b"),
                "score": 0.99,
            },
            {
                "entity_type": "IN_AADHAAR",
                "pattern": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
                "score": 0.99,
            },
            {
                "entity_type": "DATE_OF_BIRTH",
                "pattern": re.compile(r"\b(?:19|20)\d{2}[-/](?:0[1-9]|1[0-2])[-/](?:0[1-9]|[12]\d|3[01])\b|\b(?:0[1-9]|1[0-2])/(?:0[1-9]|[12]\d|3[01])/(?:19|20)\d{2}\b"),
                "score": 0.99,
            },
            {
                "entity_type": "DRIVER_LICENSE",
                "pattern": re.compile(r"(?i)\bDL-[A-Za-z0-9]+\b"),
                "score": 0.99,
            },
            {
                "entity_type": "DRIVER_LICENSE",
                "pattern": re.compile(r"(?i)\bDriver\'s License[:\s]+([A-Za-z0-9\-]+)\b"),
                "score": 0.99,
                "group": 1,
            },
            {
                "entity_type": "PASSPORT",
                "pattern": re.compile(r"(?i)\bPassport(?:\s+No)?[:\s]*([A-Z0-9]+)\b"),
                "score": 0.99,
                "group": 1,
            },
            {
                "entity_type": "CARD_PIN",
                "pattern": re.compile(r"(?i)\b(?:pin|atm\s*pin|debit\s*card\s*pin|debit\s*pin|card\s*pin|cvv|cvc|otp|secret\s*pin)[:\s=]*(\d{3,6})\b"),
                "score": 0.99,
                "group": 1,
            },
            {
                "entity_type": "BANK_ACCOUNT",
                "pattern": re.compile(r"(?i)\b(?:bank account|account\s*(?:no|number)?|acct)[:\s=]*(\d{6,18})\b"),
                "score": 0.99,
                "group": 1,
            },
            {
                "entity_type": "BANK_ACCOUNT",
                "pattern": re.compile(r"(?i)\b(?:routing\s*(?:no|number)?|routing)[:\s=]*(\d{9})\b"),
                "score": 0.99,
                "group": 1,
            },
            {
                "entity_type": "CREDIT_CARD",
                "pattern": re.compile(r"\b(?:\d{4}[-\s]?(?:[0-9xX]{4}[-\s]?){2}\d{4}|\d{13,19})\b"),
                "score": 0.99,
            },
            {
                "entity_type": "SYNTHETIC_ID",
                "pattern": re.compile(r"(?i)\b(?:Biometric Hash[:\s]*)?(sha256:[a-f0-9]{32,64}|(?:SYNTH-ID|AUTH-KEY|USER-REF)-\d+)\b"),
                "score": 0.98,
                "group": 1,
            },
            {
                "entity_type": "LOCATION",
                "pattern": re.compile(r"(?i)\b(?:Residential Address|Billing Address|Address)[:\s]+([^,\n\(\)]+(?:,\s*[^,\n\(\)]+){1,3}?,\s*[A-Z]{2}\s*\d{5}(?:-\d{4})?)\b"),
                "score": 0.96,
                "group": 1,
            },
            {
                "entity_type": "PERSON",
                "pattern": re.compile(r"(?i)\b(?:profile for|name[:\s]+|customer[:\s]+|user[:\s]+|employee[:\s]+|mr\.?|mrs\.?|ms\.?|dr\.?)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b"),
                "score": 0.95,
                "group": 1,
            },
            {
                # Context-based phone: strip \s from char class to avoid
                # greedily capturing trailing spaces and creating duplicate spans
                "entity_type": "PHONE_NUMBER",
                "pattern": re.compile(r"(?i)\b(?:mobile|phone|cell|tel|landline|home landline)[:\s]*(\+?[0-9\-\(\)]{7,18})\b"),
                "score": 0.95,
                "group": 1,
            },
            {
                "entity_type": "PHONE_NUMBER",
                "pattern": re.compile(r"\b(?:\+1[-.\s]?)?\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b|\b(?:\+91[-\s]?)?[6-9]\d{9}\b"),
                "score": 0.92,
            },
            {
                "entity_type": "PASSPORT",
                "pattern": re.compile(r"\b[A-Z][0-9]{7,9}\b"),
                "score": 0.90,
            },
            {
                "entity_type": "IP_ADDRESS",
                "pattern": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
                "score": 0.85,
            },
            {
                "entity_type": "URL",
                "pattern": re.compile(r"https?://[^\s]+"),
                "score": 0.85,
            },
        ]

    @property
    def gemini_status(self) -> Dict[str, Any]:
        """Returns current Gemini API status (active, quota_exhausted, or disabled)."""
        if self.client is None:
            return {"status": "disabled", "reason": "No API key or client init failed"}
        if self._quota_exhausted:
            remaining = 0
            if self._quota_reset_at:
                remaining = max(0, int(self._quota_reset_at - time.time()))
            hours, secs = divmod(remaining, 3600)
            mins = secs // 60
            return {
                "status": "quota_exhausted",
                "reason": "Daily free-tier quota exceeded (20 req/day)",
                "resets_in_seconds": remaining,
                "resets_in": f"{hours}h {mins}m",
                "fallback": "regex-only detection active",
            }
        return {"status": "active", "model": self.model_name}

    def _call_gemini(self, text: str) -> List[PIISpan]:
        """Call Google Gemini API to detect PII entities in text."""
        if not self.client:
            return []

        # Skip if quota is known to be exhausted and reset time hasn't passed
        if self._quota_exhausted and self._quota_reset_at:
            if time.time() < self._quota_reset_at:
                remaining = int(self._quota_reset_at - time.time())
                hours, secs = divmod(remaining, 3600)
                print(f"[PIIDetector] Quota exhausted. Skipping Gemini call. Resets in {hours}h {secs//60}m. Using regex fallback.")
                return []
            else:
                # Quota likely reset — try again
                self._quota_exhausted = False
                self._quota_reset_at = None
                print("[PIIDetector] Quota reset window passed. Retrying Gemini API.")

        try:
            config = types.GenerateContentConfig(
                system_instruction=PII_SYSTEM_PROMPT,
                temperature=0.0,
                max_output_tokens=4096,
                response_mime_type="application/json",
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=text,
                config=config,
            )
            raw = (response.text or "").strip()

            if not raw:
                return []

            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)

            entities = json.loads(raw)

            if not isinstance(entities, list):
                return []

            # Successful call — clear any quota flag
            self._quota_exhausted = False

            spans: List[PIISpan] = []
            for ent in entities:
                value = str(ent.get("value", "")).strip()
                raw_type = str(ent.get("entity_type", "PII")).upper()
                entity_type = ENTITY_TYPE_MAP.get(raw_type, raw_type)
                score = float(ent.get("score", 0.90))

                if not value or len(value) < 2:
                    continue

                # Find all occurrences of this value in text
                escaped = re.escape(value)
                matches = list(re.finditer(escaped, text, flags=re.IGNORECASE))
                if not matches:
                    continue

                for m in matches:
                    spans.append(PIISpan(
                        entity_type=entity_type,
                        start=m.start(),
                        end=m.end(),
                        score=round(score, 4),
                    ))

            return spans

        except Exception as e:
            err_str = str(e)
            # Handle quota exhaustion (429) — parse retry delay if available
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                self._quota_exhausted = True
                retry_seconds = 86400  # Default: 24h
                import re as _re
                match = _re.search(r"retry[_ ]in[\s\']*(\d+)s", err_str, _re.IGNORECASE)
                if match:
                    retry_seconds = int(match.group(1))
                self._quota_reset_at = time.time() + retry_seconds
                hours, secs = divmod(retry_seconds, 3600)
                print(f"[PIIDetector] ⚠️  Gemini quota EXHAUSTED. Resets in {hours}h {secs//60}m. Switching to regex-only fallback.")
            else:
                print(f"[PIIDetector] Gemini API call failed: {e}")
            return []

    def _run_regex(self, text: str) -> List[PIISpan]:
        """Run regex-based pattern matching for structured PII formats."""
        spans = []
        for rule in self.regex_patterns:
            group_idx = rule.get("group", 0)
            for match in rule["pattern"].finditer(text):
                start = match.start(group_idx)
                end = match.end(group_idx)
                if start != -1 and end != -1:
                    spans.append(PIISpan(
                        entity_type=rule["entity_type"],
                        start=start,
                        end=end,
                        score=rule["score"],
                    ))
        return spans

    def deduplicate_spans(self, results: List[PIISpan]) -> List[PIISpan]:
        """Filters out overlapping span results, retaining the highest scoring / longest match."""
        if not results:
            return []

        # Sort by length desc, then score desc
        sorted_res = sorted(
            results,
            key=lambda x: (x.end - x.start, x.score),
            reverse=True,
        )

        deduped: List[PIISpan] = []
        for r in sorted_res:
            overlap = False
            for existing in deduped:
                if not (r.end <= existing.start or r.start >= existing.end):
                    overlap = True
                    break
            if not overlap:
                deduped.append(r)

        return sorted(deduped, key=lambda x: x.start)

    def analyze_text(self, text: str) -> List[PIISpan]:
        """Detect PII in text using Google Gemini AI + regex patterns.

        Returns a list of PIISpan objects compatible with the gateway
        and tokenizer pipelines.
        """
        if not text or not isinstance(text, str):
            return []

        # Run both detection strategies in parallel
        gemini_spans = self._call_gemini(text)
        regex_spans = self._run_regex(text)

        # Merge: Gemini results first (higher quality), then regex
        all_spans = gemini_spans + regex_spans
        return self.deduplicate_spans(all_spans)

    def anonymize_text(self, text: str, results: Optional[List[PIISpan]] = None) -> str:
        """Replace detected PII spans with redaction placeholders like <PERSON>, <EMAIL_ADDRESS>."""
        if not text or not isinstance(text, str):
            return text
        if results is None:
            results = self.analyze_text(text)
        if not results:
            return text

        # Sort descending by start to avoid index shifting
        sorted_results = sorted(results, key=lambda x: x.start, reverse=True)
        anonymized = text
        for span in sorted_results:
            placeholder = f"[REDACTED_{span.entity_type}]"
            anonymized = anonymized[:span.start] + placeholder + anonymized[span.end:]
        return anonymized

    def extract_pii_entities(self, text: str) -> List[Dict[str, Any]]:
        """Returns structured dicts of detected PII with type, value, start, end, score."""
        results = self.analyze_text(text)
        entities = []
        for r in results:
            entities.append({
                "entity_type": r.entity_type,
                "value": text[r.start:r.end],
                "start": r.start,
                "end": r.end,
                "score": round(r.score, 2),
            })
        return entities

    def analyze_payload(self, data: Any) -> List[Dict[str, Any]]:
        """Recursively scans dicts/lists for string values containing PII."""
        detected: List[Dict[str, Any]] = []
        if isinstance(data, str):
            entities = self.extract_pii_entities(data)
            detected.extend(entities)
        elif isinstance(data, dict):
            for k, v in data.items():
                detected.extend(self.analyze_payload(v))
        elif isinstance(data, list):
            for item in data:
                detected.extend(self.analyze_payload(item))
        return detected
