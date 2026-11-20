import os


def build_headers():
    token = os.environ["BILLING_API_TOKEN"]
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}
