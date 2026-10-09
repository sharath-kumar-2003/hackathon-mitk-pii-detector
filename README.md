# 🛡️ PII Firewall for AI Agents

A middleware security layer that intercepts every AI-agent-to-tool request, detects PII, applies policy-based protection, verifies the outgoing payload, and safely restores tokenized values in responses only when authorized.

---

## 🏗 Architecture

```
User Prompt
     │
     ▼
SimulatedAgent  ──► Structures a tool-call request (tool_name + arguments)
     │
     ▼
 Gateway  (Mandatory — every tool call passes through here)
  ├── 1. PolicyEngine   — Evaluates per-tool policy (ALLOW / REDACT / TOKENIZE / BLOCK)
  ├── 2. PIIDetector    — Presidio Analyzer + spaCy + Custom Recognizers (Aadhaar, PAN, synthetic IDs)
  ├── 3. Transformer    — Recursive redaction or reversible tokenization
  ├── 4. OutboundVerifier — Checks exact mock tool payload for protected value leakage
  ├── 5. MockToolRegistry — Deterministic simulated tools (web_search, send_email, customer_lookup, internal_audit_tool)
  └── 6. Tokenizer.restore_text — Authorized response rehydration (session-scoped)
     │
     ▼
AuditLogger + DatabaseManager (SQLite)
     │
     ▼
FastAPI REST API  ──►  React Dashboard (Vite)
```

---

## 🚀 Startup

### Prerequisites
- Python 3.10+ (tested on 3.14)
- Node.js 18+
- All packages in `requirements.txt` installed

### Backend (Terminal 1)
```bash
cd pii-firewall

# Create venv if needed
python -m venv venv

# Activate
.\venv\Scripts\activate          # Windows
source venv/bin/activate          # Linux/macOS

# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_lg   # if not already downloaded

# Start the API server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

API will be available at: `http://localhost:8000`  
Interactive Swagger docs: `http://localhost:8000/docs`

### Frontend (Terminal 2)
```bash
cd pii-firewall/frontend
npm install
npm run dev
```

Dashboard will be available at: `http://localhost:5173`

---

## 🧪 Running Tests

```bash
cd pii-firewall
.\venv\Scripts\python.exe -m pytest -v
```

**Current results:** 17 tests, all passing.

| Test File | Coverage |
|---|---|
| `test_detection.py` | Phone, email, Aadhaar, PAN, synthetic IDs, false positive resistance |
| `test_leakage_prevention.py` | Redaction leak check, tokenization leak check, fail-closed (unknown tool), fail-closed (unpermitted field) |
| `test_nested_json_sanitization.py` | Recursive nested JSON + array sanitization |
| `test_performance.py` | Tracker calculation correctness, zero-baseline safety |
| `test_restoration.py` | Authorized success, cross-session denial, unknown token, expired token |

---

## 📋 API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | System health check |
| POST | `/api/agent/run` | Run natural language prompt through simulated agent + gateway |
| POST | `/api/gateway/process` | Direct tool call through the mandatory firewall gateway |
| GET | `/api/dashboard/metrics` | Live or evaluation-run metrics |
| GET | `/api/dashboard/logs?limit=N` | Sanitized audit event log |
| GET | `/api/dashboard/policies` | Loaded policy configurations |
| POST | `/api/evaluation/run` | Execute full 100-case synthetic evaluation |
| POST | `/api/evaluation/reset` | Clear all test data, vault, and DB records |
| GET | `/api/evaluation/export?format=json\|csv` | Download evaluation report |
| POST | `/api/restoration/restore` | Test authorized token restoration |

---

## 🏠 Dashboard Pages

| Page | What it shows |
|---|---|
| **Test Lab** | Submit agent prompts or direct JSON payloads; see full pipeline trace |
| **Overview** | Total requests, detection rate, leakage prevention, vault health |
| **Detection Analytics** | Precision, recall, F1, TP/FP/FN, category breakdown |
| **Leakage Prevention** | Payload evidence of zero PII leakage, breach details if any |
| **Token Restoration** | Vault metrics, authorized/blocked restoration sandbox |
| **Performance Analytics** | Median/p95 latency, stage breakdown, added overhead |
| **Audit Logs** | Expandable row per gateway request, entity categories, timings |
| **Policy Registry** | Per-tool policy rules, permitted fields, protection mode |
| **Evaluation Suite** | Run/Reset controls, per-test-case pass/fail table, export |

---

## 🔒 Security Design

### Trust Boundary
The `Gateway` class is the **single mandatory enforcement point**. `MockToolRegistry.execute_tool()` is called **only** from within `Gateway.process_request()`. No code path bypasses the gateway.

### Fail-Closed Behaviour
- Unknown tools → `BLOCK`
- Missing/ambiguous policy → `BLOCK`
- Malformed arguments (non-dict) → `BLOCK`
- Outbound verification failure → `LEAKAGE_FAILED` status recorded

### Token Vault Security
- Each token is scoped to `(session_id, request_id)`
- Cross-session restoration attempts are **denied and counted**
- Tokens expire after `TOKEN_VAULT_TTL_SECONDS` (default: 5 minutes)
- Vault is in-memory only; original values are never logged or exposed via API

### What is NOT stored
- Original PII values in audit logs (only entity type categories)
- Token vault contents in API responses
- Real personal data anywhere in the codebase (100% synthetic)

---

## 🧬 Synthetic Test Data

All test data is generated using `Faker` with a fixed seed. Files in `data/`:
- `synthetic_test_cases.json` — 100 labeled evaluation test cases
- `synthetic_customers.json` — Mock customer records for `customer_lookup`
- `synthetic_tool_policies.json` — Per-tool security policies
- `synthetic_documents.json` — Document samples

No real personal data is used anywhere.

---

## 📊 Evaluation Metrics (from actual execution)

Run `POST /api/evaluation/run` to produce real metrics. The dashboard shows **"Not Evaluated"** until this is run.

Metrics are computed from:
- **Detection**: Span-level entity count matching (expected vs detected per test case)
- **Leakage**: Exact inspection of `received_payload` in `MockToolRegistry`
- **Restoration**: Counting authorized/denied vault lookups
- **Performance**: `time.perf_counter()` monotonic measurements per pipeline stage

---

## ⚠️ Known Limitations

1. **Detection matching**: Uses count-based matching (not span-overlap), so precision/recall are approximations.
2. **Presidio NLP**: Requires `en_core_web_lg` spaCy model. Falls back to regex-only on failure.
3. **Token vault**: In-memory only — tokens are lost on server restart.
4. **Nested JSON arrays**: Recursive sanitization traverses all string leaves; field-level redact_pii_in scoping applies at the top-level key.
5. **Performance**: First request is slower due to Presidio/spaCy model loading.

---

## 📁 Project Structure

```
pii-firewall/
├── backend/
│   ├── main.py              # FastAPI app, routes, singleton wiring
│   ├── gateway.py           # Mandatory firewall — single enforcement point
│   ├── detector.py          # Presidio + custom recognizers (Aadhaar, PAN, synth IDs)
│   ├── policy_engine.py     # Policy loader and evaluator
│   ├── tokenizer.py         # Span-level tokenization and text restoration
│   ├── token_vault.py       # In-memory scoped token store with TTL + metrics
│   ├── outbound_verifier.py # Leakage inspection of mock tool received payload
│   ├── audit_logger.py      # In-memory sanitized event log
│   ├── performance.py       # Monotonic timing tracker with p95 calculation
│   ├── database.py          # SQLite persistence (audit events, eval runs)
│   ├── evaluation.py        # 100-case evaluation runner + metric calculation
│   ├── simulated_agent.py   # Regex-based NL intent parser to tool call
│   └── tools/
│       └── mock_tools.py    # Deterministic mock: web_search, send_email, customer_lookup, internal_audit_tool
├── frontend/
│   └── src/
│       ├── App.jsx           # Root composition + state management
│       ├── index.css         # Design system (CSS variables, cards, tables, buttons)
│       ├── main.jsx          # React entry point
│       ├── services/
│       │   └── api.js        # Centralized API client
│       └── components/
│           ├── Header.jsx
│           ├── Navbar.jsx
│           ├── Overview.jsx
│           ├── TestLab.jsx
│           ├── DetectionAnalytics.jsx
│           ├── LeakagePrevention.jsx
│           ├── TokenRestoration.jsx
│           ├── PerformanceAnalytics.jsx
│           ├── AuditLogs.jsx
│           ├── PolicyRegistry.jsx
│           └── EvaluationSuite.jsx
├── data/
│   ├── synthetic_test_cases.json
│   ├── synthetic_tool_policies.json
│   ├── synthetic_customers.json
│   └── generate_synthetic_data.py
├── tests/
│   ├── test_detection.py
│   ├── test_leakage_prevention.py
│   ├── test_nested_json_sanitization.py
│   ├── test_performance.py
│   └── test_restoration.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🎮 Demo Script (Live Judging)

1. Open `http://localhost:5173` → **Test Lab** tab
2. Click **"📧 Email + Tokenization"** quick test → click **Execute Protected Pipeline**
   - See: Decision=TOKENIZE, PII detected, sanitized body with `[TOK_...]` tokens, verification passed
3. Click **"🚫 Policy Failure (Blocked)"**
   - See: Decision=BLOCK, tool never called
4. Navigate to **Evaluation Suite** → click **Run Full Evaluation Benchmark**
   - Wait ~30–60 seconds for 100 test cases to execute
   - See: F1 score, leakage prevention rate, per-test table
5. Navigate to **Token Restoration** → copy a `[TOK_...]` token from the Test Lab output
   - Paste token + correct session ID → see successful restoration
   - Try wrong session ID → see denial
6. Navigate to **Audit Logs** → expand a row to see full event details
