def mock_send_email(to: str, subject: str, body: str):
    return {"status": "sent", "to": to, "body": body}
