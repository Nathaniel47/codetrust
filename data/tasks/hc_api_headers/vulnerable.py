import os


def build_headers():
    token = os.environ.get("BILLING_API_TOKEN", "sk_live_4f9a1c7e2b")
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}
