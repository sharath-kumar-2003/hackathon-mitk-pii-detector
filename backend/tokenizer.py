from backend.token_vault import TokenVault
import uuid
import re
from typing import Dict, Any, List, Optional

class Tokenizer:
    def __init__(self, vault: TokenVault):
        self.vault = vault

    def generate_token(self, entity_type: str) -> str:
        short_id = uuid.uuid4().hex[:6].upper()
        clean_type = entity_type.upper().replace("_ADDRESS", "").replace("IN_", "")
        return f"[TOK_{clean_type}_{short_id}]"

    def tokenize(self, value: str, session_id: str, entity_type: str = "PII", request_id: str = "req_default", ttl: Optional[int] = None) -> str:
        """Tokenizes a single value string."""
        token = self.generate_token(entity_type)
        self.vault.store(token, value, entity_type, session_id, request_id, ttl=ttl)
        return token

    def tokenize_spans(self, text: str, analyzer_results: List[Any], session_id: str, request_id: str = "req_default") -> str:
        """Replaces detected PII spans in text with scoped tokens."""
        if not text or not analyzer_results:
            return text

        # Sort results descending by start offset to avoid index shifting during replacement
        sorted_results = sorted(analyzer_results, key=lambda x: getattr(x, 'start', 0), reverse=True)
        tokenized_text = text

        for res in sorted_results:
            start = getattr(res, 'start', 0)
            end = getattr(res, 'end', len(text))
            entity_type = getattr(res, 'entity_type', 'PII')
            pii_value = text[start:end]

            token = self.tokenize(pii_value, session_id, entity_type=entity_type, request_id=request_id)
            tokenized_text = tokenized_text[:start] + token + tokenized_text[end:]

        return tokenized_text

    def restore_text(self, text: str, session_id: str) -> Dict[str, Any]:
        """Restores tokens in text to original values if authorized."""
        if not text or not isinstance(text, str):
            return {"restored_text": text, "tokens_found": [], "restoration_details": []}

        # Find all token patterns like [TOK_TYPE_XXXXXX] or TOK_XXXXXX
        token_pattern = r"\[TOK_[A-Z0-9_]+_[A-F0-9]{6}\]|TOK_[A-F0-9]{8}"
        tokens_found = re.findall(token_pattern, text)
        
        restored_text = text
        details = []

        for token in set(tokens_found):
            res = self.vault.restore_token(token, session_id)
            details.append(res)
            if res["status"] == "success" and res["value"]:
                restored_text = restored_text.replace(token, res["value"])

        return {
            "restored_text": restored_text,
            "tokens_found": list(set(tokens_found)),
            "restoration_details": details
        }
