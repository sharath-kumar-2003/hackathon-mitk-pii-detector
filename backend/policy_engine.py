import json
import os
from typing import Dict, Any, Optional

class PolicyEngine:
    def __init__(self, policies_path: str):
        self.policies_path = policies_path
        self.reload_policies()

    def reload_policies(self):
        if os.path.exists(self.policies_path):
            with open(self.policies_path, 'r') as f:
                self.policies = json.load(f)
        else:
            self.policies = []

    def get_policy(self, tool_name: str) -> Optional[Dict[str, Any]]:
        for policy in self.policies:
            if policy["tool_name"] == tool_name:
                return policy
        return None

    def evaluate_request(self, tool_name: str, arguments: Any) -> Dict[str, Any]:
        """
        Evaluates a tool-call request against configured policy rules.
        Returns policy decision (ALLOW, REDACT, TOKENIZE, BLOCK), reason, and field rules.
        """
        policy = self.get_policy(tool_name)
        
        # Policy Failure 1: Unknown tool or missing policy config (Fail Closed)
        if not policy:
            return {
                "decision": "BLOCK",
                "action": "BLOCK",
                "reason": f"Unknown tool '{tool_name}' or missing policy configuration. Request blocked (fail-closed).",
                "policy": None
            }

        # Policy Failure 2: Malformed tool argument payload
        if not isinstance(arguments, dict):
            return {
                "decision": "BLOCK",
                "action": "BLOCK",
                "reason": f"Malformed arguments for tool '{tool_name}'. Expected JSON object/dict but received {type(arguments).__name__}.",
                "policy": policy
            }

        permitted_fields = policy.get("permitted_fields", [])
        block_if_unpermitted = policy.get("block_if_unpermitted_field", True)

        # Check for unpermitted fields
        unpermitted = [k for k in arguments.keys() if k not in permitted_fields]
        if unpermitted and block_if_unpermitted:
            return {
                "decision": "BLOCK",
                "action": "BLOCK",
                "reason": f"Security Policy Violation: Field(s) {unpermitted} are not permitted for tool '{tool_name}'. Allowed: {permitted_fields}.",
                "policy": policy
            }

        action = policy.get("action", "redact")
        description = policy.get("description", "Policy rule applied.")

        if action == "allow":
            return {
                "decision": "ALLOW",
                "action": "ALLOW",
                "reason": f"Policy ALLOW: Tool '{tool_name}' is explicitly authorized to receive permitted fields {permitted_fields}.",
                "policy": policy
            }
        elif action == "tokenize":
            return {
                "decision": "TOKENIZE",
                "action": "TOKENIZE",
                "reason": f"Policy TOKENIZE: PII in permitted fields {policy.get('redact_pii_in', [])} will be replaced with reversible scoped tokens.",
                "policy": policy
            }
        elif action == "redact":
            return {
                "decision": "REDACT",
                "action": "REDACT",
                "reason": f"Policy REDACT: PII in permitted fields {policy.get('redact_pii_in', [])} will be permanently masked.",
                "policy": policy
            }
        else:
            return {
                "decision": "BLOCK",
                "action": "BLOCK",
                "reason": f"Invalid policy action '{action}' configured for tool '{tool_name}'.",
                "policy": policy
            }
