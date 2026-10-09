import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from detector import PIIDetector

detector = PIIDetector()
args = {
    "to": "test.account@example.com",
    "subject": "Customer Notification",
    "body": "Send email to test.account@example.com with body containing phone 9000000001 and Aadhaar 1234 5678 9012"
}
print(detector.analyze_payload(args))
