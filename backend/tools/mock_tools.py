import json
import os
from typing import Dict, Any, List

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data")

class MockToolRegistry:
    def __init__(self):
        self.received_payloads: List[Dict[str, Any]] = []
        self._load_synthetic_customers()

    def _load_synthetic_customers(self):
        cust_path = os.path.join(DATA_DIR, "synthetic_customers.json")
        if os.path.exists(cust_path):
            with open(cust_path, "r") as f:
                self.customers = json.load(f)
        else:
            self.customers = []

    def clear_payload_history(self):
        self.received_payloads.clear()

    def execute_tool(self, tool_name: str, sanitized_arguments: Dict[str, Any], session_id: str = "default_session", is_baseline_check: bool = False) -> Dict[str, Any]:
        """Executes a mock tool and records the EXACT payload received by the mock tool."""
        # Record payload received by the mock tool for outbound leakage verification (only for non-baseline runs)
        if not is_baseline_check:
            record = {
                "tool_name": tool_name,
                "received_arguments": sanitized_arguments,
                "session_id": session_id
            }
            self.received_payloads.append(record)

        if tool_name == "web_search":
            query = sanitized_arguments.get("query", "")
            return {
                "status": "success",
                "tool": "web_search",
                "results": [
                    f"Search result 1 for: {query}",
                    f"Search result 2 for: {query}"
                ],
                "received_payload": sanitized_arguments
            }

        elif tool_name == "send_email":
            to_addr = sanitized_arguments.get("to", "")
            subject = sanitized_arguments.get("subject", "")
            body = sanitized_arguments.get("body", "")
            return {
                "status": "sent",
                "tool": "send_email",
                "recipient": to_addr,
                "response_body": f"Email queued successfully for delivery to {to_addr}. Body reference: {body}",
                "received_payload": sanitized_arguments
            }

        elif tool_name == "customer_lookup":
            cust_id = sanitized_arguments.get("customer_id", "")
            fields = sanitized_arguments.get("fields", ["name", "email", "status"])
            
            customer = next((c for c in self.customers if c["id"] == cust_id), None)
            if not customer:
                # Return generic synthetic result if ID not found in fixed dataset
                customer = {
                    "id": cust_id or "cust_1001",
                    "name": "Synthetic User",
                    "email": "synthetic.user@example.com",
                    "phone": "9000000001",
                    "status": "active"
                }

            filtered_customer = {k: v for k, v in customer.items() if k in fields or k == "id"}
            return {
                "status": "success",
                "tool": "customer_lookup",
                "customer": filtered_customer,
                "received_payload": sanitized_arguments
            }

        elif tool_name == "internal_audit_tool":
            return {
                "status": "audited",
                "tool": "internal_audit_tool",
                "audit_id": "AUD-998811",
                "details": f"Audit record created for user reference {sanitized_arguments.get('user_reference', 'N/A')}",
                "received_payload": sanitized_arguments
            }

        elif tool_name == "document_summarizer":
            content = sanitized_arguments.get("content", "")
            title = sanitized_arguments.get("title", "Untitled Document")
            words = content.split() if content else []
            word_count = len(words)
            summary = " ".join(words[:20]) + ("..." if word_count > 20 else "")
            return {
                "status": "summarized",
                "tool": "document_summarizer",
                "title": title,
                "word_count": word_count,
                "summary": summary,
                "received_payload": sanitized_arguments
            }

        else:
            raise ValueError(f"Unknown mock tool: {tool_name}")

