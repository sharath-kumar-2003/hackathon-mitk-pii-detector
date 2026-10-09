import re
import os
import json
from typing import Dict, Any, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from google import genai
from google.genai import types

AGENT_SYSTEM_PROMPT = """You are an AI Agent with access to specific tools.
Given a user prompt, choose the most appropriate tool and generate the structured JSON arguments.

Available Tools:
1. "customer_lookup": Use when searching, querying, or finding customer details.
   Arguments:
   - "customer_id": string (e.g. "cust_1001", "cust_1005" or extracted ID)
   - "fields": array of strings (e.g. ["id", "name", "email", "status"])

2. "send_email": Use when sending messages, alerts, or emails.
   Arguments:
   - "to": recipient email address (string)
   - "subject": subject line (string)
   - "body": message content containing the user's details/prompt (string)

3. "internal_audit_tool": Use when auditing, verifying compliance, or logging records (PAN, Aadhaar, compliance notes).
   Arguments:
   - "report_name": string (e.g. "Compliance Audit Report")
   - "user_reference": string (e.g. "REF-SESSION-99" or user ID)
   - "notes": details or prompt text (string)

4. "document_summarizer": Use when summarizing notes, articles, or documents.
   Arguments:
   - "title": document title (string)
   - "content": document text (string)

5. "web_search": Default fallback for general queries, web lookups, or information retrieval.
   Arguments:
   - "query": search query string

Respond ONLY with a JSON object in this exact format:
{
  "tool_name": "one_of_the_above_tools",
  "arguments": { ... }
}
"""

class SimulatedAgent:
    """Intelligent AI Agent powered by Google Gemini with deterministic fallback."""

    def __init__(self):
        api_key = os.environ.get("GEMINI_API_KEY", "")
        self.model_name = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
        if api_key:
            try:
                self.client = genai.Client(api_key=api_key)
                print(f"[SimulatedAgent] Google Gemini AI agent initialized ({self.model_name}).")
            except Exception as e:
                print(f"[SimulatedAgent] Gemini init failed: {e}. Using heuristic routing.")
                self.client = None
        else:
            self.client = None

    def _call_gemini_routing(self, prompt: str) -> Optional[Dict[str, Any]]:
        """Uses Gemini to reason and choose the right tool and parameters."""
        if not self.client:
            return None

        try:
            config = types.GenerateContentConfig(
                system_instruction=AGENT_SYSTEM_PROMPT,
                temperature=0.0,
                max_output_tokens=1024,
                response_mime_type="application/json",
            )
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=f"User request: {prompt}",
                config=config,
            )
            raw = (response.text or "").strip()
            if not raw:
                return None

            if raw.startswith("```"):
                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)

            parsed = json.loads(raw)
            if "tool_name" in parsed and "arguments" in parsed:
                return parsed
        except Exception as e:
            print(f"[SimulatedAgent] Gemini agent call failed: {e}. Falling back to heuristics.")

        return None

    def _heuristic_routing(self, prompt: str) -> Dict[str, Any]:
        """Fast, deterministic fallback routing using pattern matching."""
        # Intent 1: Customer lookup
        cust_match = re.search(r"cust_\d+", prompt, re.IGNORECASE)
        if cust_match or "customer" in prompt.lower() or "lookup" in prompt.lower():
            cust_id = cust_match.group(0) if cust_match else "cust_1001"
            return {
                "tool_name": "customer_lookup",
                "arguments": {
                    "customer_id": cust_id,
                    "fields": ["id", "name", "email", "status"]
                }
            }

        # Intent 2: Email sending
        email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", prompt)
        if "email" in prompt.lower() or "send" in prompt.lower() or email_match:
            to_addr = email_match.group(0) if email_match else "test@example.com"
            return {
                "tool_name": "send_email",
                "arguments": {
                    "to": to_addr,
                    "subject": "AI Agent Automated Notification",
                    "body": prompt
                }
            }

        # Intent 3: Internal audit
        if "audit" in prompt.lower() or "pan" in prompt.lower() or "aadhaar" in prompt.lower():
            return {
                "tool_name": "internal_audit_tool",
                "arguments": {
                    "report_name": "Automated System Compliance Audit",
                    "user_reference": "REF-SESSION-99",
                    "notes": prompt
                }
            }

        # Intent 4: Document summarization
        if "summarize" in prompt.lower() or "summary" in prompt.lower() or "document" in prompt.lower():
            return {
                "tool_name": "document_summarizer",
                "arguments": {
                    "title": "User Submitted Document",
                    "content": prompt
                }
            }

        # Default Intent: Web search
        return {
            "tool_name": "web_search",
            "arguments": {
                "query": prompt
            }
        }

    def handle_request(self, user_request: str, session_id: str = "session_default") -> Dict[str, Any]:
        """Converts a natural language user prompt into a structured tool-call request."""
        prompt = user_request.strip()

        # Try AI-driven tool selection first
        gemini_result = self._call_gemini_routing(prompt)
        if gemini_result and isinstance(gemini_result.get("arguments"), dict):
            return {
                "tool_name": gemini_result["tool_name"],
                "arguments": gemini_result["arguments"],
                "session_id": session_id
            }

        # Fall back to heuristic routing
        heuristic = self._heuristic_routing(prompt)
        return {
            "tool_name": heuristic["tool_name"],
            "arguments": heuristic["arguments"],
            "session_id": session_id
        }
