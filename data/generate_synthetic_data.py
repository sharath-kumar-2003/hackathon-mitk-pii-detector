import json
import os
import random
from faker import Faker

fake = Faker('en_IN')
Faker.seed(42)
random.seed(42)

DATA_DIR = os.path.dirname(os.path.abspath(__file__))

def generate_customers(count=50):
    customers = []
    for i in range(count):
        customers.append({
            "id": f"cust_{1000+i}",
            "name": fake.name(),
            "email": fake.email(),
            "phone": fake.phone_number(),
            "address": fake.address().replace('\n', ', '),
            "aadhaar": f"{random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)}",
            "pan": fake.bothify(text='?????####?').upper(),
            "status": random.choice(["active", "inactive"])
        })
    with open(os.path.join(DATA_DIR, "synthetic_customers.json"), "w") as f:
        json.dump(customers, f, indent=2)

def generate_documents():
    docs = [
        {"id": "doc_1", "content": "The meeting was attended by John Doe (johndoe@example.com). They discussed project X."},
        {"id": "doc_2", "content": f"Confidential: Salary for {fake.name()} has been updated to 50000. Phone: {fake.phone_number()}."}
    ]
    with open(os.path.join(DATA_DIR, "synthetic_documents.json"), "w") as f:
        json.dump(docs, f, indent=2)

def generate_tool_policies():
    policies = [
        {
            "tool_name": "web_search",
            "permitted_fields": ["query"],
            "redact_pii_in": ["query"],
            "block_if_unpermitted_field": True,
            "action": "redact",
            "description": "Public search tool. Redacts all PII in search query."
        },
        {
            "tool_name": "send_email",
            "permitted_fields": ["to", "subject", "body"],
            "redact_pii_in": ["body"],
            "block_if_unpermitted_field": True,
            "action": "tokenize",
            "description": "Email delivery tool. Tokenizes PII in body so original content can be restored."
        },
        {
            "tool_name": "customer_lookup",
            "permitted_fields": ["customer_id", "fields"],
            "redact_pii_in": [],
            "block_if_unpermitted_field": True,
            "action": "allow",
            "description": "Internal CRM lookup tool. Allows querying customer by synthetic customer reference ID."
        },
        {
            "tool_name": "internal_audit_tool",
            "permitted_fields": ["report_name", "user_reference", "notes"],
            "redact_pii_in": ["notes"],
            "block_if_unpermitted_field": True,
            "action": "tokenize",
            "description": "Audit logging tool. Tokenizes sensitive notes."
        }
    ]
    with open(os.path.join(DATA_DIR, "synthetic_tool_policies.json"), "w") as f:
        json.dump(policies, f, indent=2)

def generate_test_cases():
    cases = []
    case_id = 1

    # Category 1: Email Detection & Tokenization (15 cases)
    for i in range(15):
        email = f"user_{i+100}@example.com"
        name = fake.name()
        cases.append({
            "id": f"TC-{case_id:03d}",
            "category": "EMAIL_ADDRESS",
            "tool_name": "send_email",
            "user_prompt": f"Send email to {email} regarding account update for {name}.",
            "arguments": {
                "to": email,
                "subject": "Account Update",
                "body": f"Dear {name}, please update your security settings at {email}."
            },
            "expected_pii": [
                {"type": "EMAIL_ADDRESS", "value": email},
                {"type": "PERSON", "value": name}
            ],
            "protected_values": [email, name],
            "expected_action": "tokenize",
            "expected_outcome": "sanitized",
            "has_pii": True
        })
        case_id += 1

    # Category 2: Phone Number Detection & Redaction (15 cases)
    phone_samples = [
        "9876543210", "+91 9123456789", "9000000001", "8888877777", "+91-9988776655",
        "98765 43210", "7012345678", "+91 8000011122", "9444455555", "9333322222",
        "8111122223", "+91 7890123456", "9555566667", "9666677778", "9777788889"
    ]
    for p in phone_samples:
        cases.append({
            "id": f"TC-{case_id:03d}",
            "category": "PHONE_NUMBER",
            "tool_name": "web_search",
            "user_prompt": f"Search contact information for helpline {p}",
            "arguments": {
                "query": f"Find status for customer helpline number {p}"
            },
            "expected_pii": [
                {"type": "PHONE_NUMBER", "value": p}
            ],
            "protected_values": [p],
            "expected_action": "redact",
            "expected_outcome": "sanitized",
            "has_pii": True
        })
        case_id += 1

    # Category 3: Indian PII Fixtures - Aadhaar & PAN (15 cases)
    aadhaar_list = [f"{random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)}" for _ in range(8)]
    pan_list = [fake.bothify(text='?????####?').upper() for _ in range(7)]
    
    for a in aadhaar_list:
        cases.append({
            "id": f"TC-{case_id:03d}",
            "category": "IN_AADHAAR",
            "tool_name": "internal_audit_tool",
            "user_prompt": f"Audit verification record with Aadhaar number {a}",
            "arguments": {
                "report_name": "Identity Verification",
                "user_reference": "REF-8821",
                "notes": f"Verified applicant using Aadhaar {a} successfully."
            },
            "expected_pii": [
                {"type": "IN_AADHAAR", "value": a}
            ],
            "protected_values": [a],
            "expected_action": "tokenize",
            "expected_outcome": "sanitized",
            "has_pii": True
        })
        case_id += 1

    for pan in pan_list:
        cases.append({
            "id": f"TC-{case_id:03d}",
            "category": "IN_PAN",
            "tool_name": "internal_audit_tool",
            "user_prompt": f"Audit tax document with PAN {pan}",
            "arguments": {
                "report_name": "Tax Compliance",
                "user_reference": "REF-9932",
                "notes": f"Tax clearance provided for PAN card holder {pan}."
            },
            "expected_pii": [
                {"type": "IN_PAN", "value": pan}
            ],
            "protected_values": [pan],
            "expected_action": "tokenize",
            "expected_outcome": "sanitized",
            "has_pii": True
        })
        case_id += 1

    # Category 4: Synthetic Identifier Patterns & Person Names (15 cases)
    syn_ids = [f"SYNTH-ID-{1000+i}" for i in range(8)]
    names = [fake.name() for _ in range(7)]

    for syn in syn_ids:
        cases.append({
            "id": f"TC-{case_id:03d}",
            "category": "SYNTHETIC_ID",
            "tool_name": "internal_audit_tool",
            "user_prompt": f"Audit test fixture identifier {syn}",
            "arguments": {
                "report_name": "Fixture Check",
                "user_reference": syn,
                "notes": f"Processing synthetic test fixture {syn} for system benchmark."
            },
            "expected_pii": [
                {"type": "SYNTHETIC_ID", "value": syn}
            ],
            "protected_values": [syn],
            "expected_action": "tokenize",
            "expected_outcome": "sanitized",
            "has_pii": True
        })
        case_id += 1

    for nm in names:
        cases.append({
            "id": f"TC-{case_id:03d}",
            "category": "PERSON",
            "tool_name": "web_search",
            "user_prompt": f"Search articles about {nm}",
            "arguments": {
                "query": f"Biographical profile for {nm}"
            },
            "expected_pii": [
                {"type": "PERSON", "value": nm}
            ],
            "protected_values": [nm],
            "expected_action": "redact",
            "expected_outcome": "sanitized",
            "has_pii": True
        })
        case_id += 1

    # Category 5: Clean Non-PII & False Positive Challenge Cases (20 cases)
    false_positive_inputs = [
        ("Query status of order ORD-987654", {"query": "Status of order ORD-987654"}, "web_search"),
        ("Check product SKU-109283 in inventory", {"query": "Inventory lookup for SKU-109283"}, "web_search"),
        ("System timestamp 2026-10-09T19:30:00Z execution", {"query": "Log event at 2026-10-09T19:30:00Z"}, "web_search"),
        ("HTTP 200 OK status code response", {"query": "Explain HTTP 200 OK status code"}, "web_search"),
        ("Python version 3.14.0 release notes", {"query": "What is new in Python version 3.14.0?"}, "web_search"),
        ("Calculate 500 + 4500 total amount", {"query": "Math calculation 500 + 4500"}, "web_search"),
        ("Hubballi weather forecast tomorrow", {"query": "Weather forecast for Hubballi city tomorrow"}, "web_search"),
        ("Database query SELECT * FROM table", {"query": "SQL syntax for SELECT * FROM table"}, "web_search"),
        ("Check server IP 127.0.0.1 loopback", {"query": "Localhost loopback address 127.0.0.1"}, "web_search"),
        ("Customer lookup by ID cust_1001", {"customer_id": "cust_1001", "fields": ["status"]}, "customer_lookup"),
        ("Customer lookup by ID cust_1005", {"customer_id": "cust_1005", "fields": ["name", "email"]}, "customer_lookup"),
        ("Customer lookup by ID cust_1020", {"customer_id": "cust_1020", "fields": ["status"]}, "customer_lookup"),
        ("Search public documentation for API route", {"query": "REST API documentation for /v1/health"}, "web_search"),
        ("Read open source license terms", {"query": "MIT License full text text details"}, "web_search"),
        ("Check server CPU utilization 45%", {"query": "Troubleshoot server CPU utilization 45 percent"}, "web_search"),
        ("Search recipe for vegetarian pasta", {"query": "Vegetarian pasta recipe with garlic and olive oil"}, "web_search"),
        ("List files in directory /usr/bin", {"query": "How to list files in /usr/bin directory"}, "web_search"),
        ("Check git commit hash a1b2c3d4e5", {"query": "Git commit hash a1b2c3d4e5 diff"}, "web_search"),
        ("Check port 8000 availability", {"query": "Check if port 8000 is open on localhost"}, "web_search"),
        ("Customer lookup by ID cust_1049", {"customer_id": "cust_1049", "fields": ["status"]}, "customer_lookup")
    ]

    for fp_prompt, fp_args, fp_tool in false_positive_inputs:
        cases.append({
            "id": f"TC-{case_id:03d}",
            "category": "CLEAN_NON_PII",
            "tool_name": fp_tool,
            "user_prompt": fp_prompt,
            "arguments": fp_args,
            "expected_pii": [],
            "protected_values": [],
            "expected_action": "allow",
            "expected_outcome": "allowed",
            "has_pii": False
        })
        case_id += 1

    # Category 6: Negative & Violation Challenge Cases (Unknown Tools, Missing Policies, Unpermitted Fields) (10 cases)
    violation_cases = [
        ("Invoke non-existent tool query_db", "query_db", {"query": "SELECT * FROM users"}, "Unknown tool Policy failure (fail closed)"),
        ("Invoke unauthorized tool execute_code", "execute_code", {"code": "import os; os.system('ls')"}, "Unknown tool Policy failure (fail closed)"),
        ("Invoke unknown tool delete_user", "delete_user", {"user_id": "user_123"}, "Unknown tool Policy failure (fail closed)"),
        ("Send unpermitted secret field to web_search", "web_search", {"query": "weather", "unpermitted_api_key": "SECRET-123456"}, "Unpermitted field in web_search"),
        ("Send unpermitted password to customer_lookup", "customer_lookup", {"customer_id": "cust_1001", "password_hash": "hash_secret_99"}, "Unpermitted field in customer_lookup"),
        ("Send unpermitted auth header to send_email", "send_email", {"to": "test@example.com", "subject": "Hi", "body": "Hello", "auth_token": "Bearer 12345"}, "Unpermitted field in send_email"),
        ("Invoke unknown tool admin_reset", "admin_reset", {"action": "reset_all"}, "Unknown tool Policy failure (fail closed)"),
        ("Invoke unknown tool export_all_data", "export_all_data", {"format": "csv"}, "Unknown tool Policy failure (fail closed)"),
        ("Send unpermitted field card_number to web_search", "web_search", {"query": "test", "credit_card": "4111222233334444"}, "Unpermitted field in web_search"),
        ("Send malformed arguments to web_search", "web_search", "NOT_A_DICT_ARGUMENT", "Malformed tool argument structure")
    ]

    for v_prompt, v_tool, v_args, v_reason in violation_cases:
        cases.append({
            "id": f"TC-{case_id:03d}",
            "category": "POLICY_VIOLATION",
            "tool_name": v_tool,
            "user_prompt": v_prompt,
            "arguments": v_args,
            "expected_pii": [],
            "protected_values": [],
            "expected_action": "block",
            "expected_outcome": "blocked",
            "has_pii": False,
            "violation_reason": v_reason
        })
        case_id += 1

    # Category 7: Multi-PII & Nested Payload Cases (10 cases)
    for i in range(10):
        e = f"contact_{i}@company.org"
        p = f"91111222{i:02d}"
        nm = fake.name()
        addr = f"{i+10} Main St, Hubballi"
        cases.append({
            "id": f"TC-{case_id:03d}",
            "category": "MULTI_PII",
            "tool_name": "send_email",
            "user_prompt": f"Email composite profile for {nm} at {e} phone {p} address {addr}",
            "arguments": {
                "to": e,
                "subject": "Composite Profile",
                "body": f"Name: {nm}, Phone: {p}, Email: {e}, Address: {addr}"
            },
            "expected_pii": [
                {"type": "EMAIL_ADDRESS", "value": e},
                {"type": "PHONE_NUMBER", "value": p},
                {"type": "PERSON", "value": nm}
            ],
            "protected_values": [e, p, nm],
            "expected_action": "tokenize",
            "expected_outcome": "sanitized",
            "has_pii": True
        })
        case_id += 1

    with open(os.path.join(DATA_DIR, "synthetic_test_cases.json"), "w") as f:
        json.dump(cases, f, indent=2)
    print(f"Generated {len(cases)} synthetic test cases.")

if __name__ == "__main__":
    generate_customers()
    generate_documents()
    generate_tool_policies()
    generate_test_cases()
    print("All synthetic data generated successfully.")
