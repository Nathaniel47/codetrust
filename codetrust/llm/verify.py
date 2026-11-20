"""Week-1 check: does each provider have the configured model, and does a tiny call work?

Run: python -m codetrust.llm.verify
Needs the CODETRUST_*_API_KEY variables. Writes the result to results/run_meta.json.
"""

import json
import sys

from codetrust.llm.meta import update_run_meta
from codetrust.llm.models import MODELS, make_client
from codetrust.llm.providers import ProviderError, api_key, list_model_ids


def verify(tags: list[str]) -> dict:
    report = {}
    for tag in tags:
        spec = MODELS[tag]
        entry = {"model_id": spec.model_id, "limits_assumed": spec.limits}
        try:
            api_key(spec.provider)
        except ProviderError as exc:
            entry["status"] = f"skipped: {exc}"
            report[tag] = entry
            continue
        try:
            available = list_model_ids(spec.provider)
            entry["listed"] = spec.model_id in available
            entry["similar"] = [m for m in available if spec.model_id.split("/")[-1][:8] in m][:8]
            client = make_client(tag, max_tokens=20, use_budget=False)
            reply = client.complete("Reply with the single word OK.")
            entry["status"] = "ok" if reply.strip() else "empty reply"
        except Exception as exc:  # report every failure kind instead of stopping
            entry["status"] = f"failed: {type(exc).__name__}: {str(exc)[:160]}"
        report[tag] = entry
    return report


if __name__ == "__main__":
    report = verify(sys.argv[1:] or list(MODELS))
    update_run_meta(model_verification=report)
    print(json.dumps(report, indent=2))
