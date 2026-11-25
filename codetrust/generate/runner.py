"""Generate code for every (task, wording, model, repeat) and store one record per generation.

Resumable: a record that already exists is skipped, and every model answer is also cached, so a
rerun never pays twice. Stops cleanly (exit code 75) when a provider's daily budget is used up.

Examples:
    python -m codetrust.generate.runner --models scripted --repeats 1
    python -m codetrust.generate.runner --models groq,gemini --tasks pilot
"""

import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from pathlib import Path

from codetrust.config import SEED, TEMPERATURE
from codetrust.generate.extract import extract_code
from codetrust.llm.budget import DailyBudgetExhausted
from codetrust.llm.meta import update_run_meta
from codetrust.llm.models import REMINDER, REMINDER_SUFFIX, SYSTEM_PROMPT, make_client
from codetrust.llm.providers import ProviderError
from codetrust.paths import DATA_DIR, RESULTS_DIR
from codetrust.tasks.loader import load_tasks

GENERATED_DIR = DATA_DIR / "generated"
EXIT_BUDGET = 75
MAX_CONSECUTIVE_ERRORS = 3


def load_paraphrases() -> list[dict]:
    path = DATA_DIR / "paraphrases.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def pilot_task_ids() -> list[str]:
    """One task from each of the first five families (alphabetical): a cheap end-to-end check."""
    seen, ids = set(), []
    for task in load_tasks():
        if task.family not in seen:
            seen.add(task.family)
            ids.append(task.id)
    return ids[:5]


def noise_task_ids(seed: int = SEED) -> list[str]:
    """The resampling-noise subset: one held-out test task per family, picked with a fixed seed."""
    split = json.loads((DATA_DIR / "splits.json").read_text(encoding="utf-8"))
    rng = random.Random(seed)
    by_family: dict[str, list[str]] = {}
    for task in load_tasks():
        if split[task.id] == "test":
            by_family.setdefault(task.family, []).append(task.id)
    return [rng.choice(sorted(by_family[f])) for f in sorted(by_family)]


def with_reminder(prompt: str) -> str:
    return prompt if REMINDER in prompt else f"{prompt}\n\n{REMINDER}"


def plan(rows: list[dict], tags: list[str], repeats: int, task_ids: set[str] | None):
    """Order work so an interrupted run still covers every task (wording is the outer loop)."""
    rows = [r for r in rows if task_ids is None or r["task_id"] in task_ids]
    for repeat in range(repeats):
        for index in range(10):
            for row in (r for r in rows if r["index"] == index):
                for tag in tags:
                    yield tag, row, repeat


def record_path(out: Path, tag: str, row: dict, repeat: int) -> Path:
    return out / tag / f"{row['task_id']}__{row['index']}__r{repeat}.json"


def run(
    tags: list[str],
    repeats: int = 1,
    task_ids: set[str] | None = None,
    limit: int | None = None,
    out: Path = GENERATED_DIR,
    clients: dict | None = None,
    reminder: bool = False,
) -> dict:
    rows = load_paraphrases()
    clients = {} if clients is None else clients
    suffix = REMINDER_SUFFIX if reminder else ""
    stats = {tag: Counter() for tag in tags}
    errors = 0
    stopped = None
    done_now = 0
    for tag, row, repeat in plan(rows, tags, repeats, task_ids):
        path = record_path(out, tag + suffix, row, repeat)
        if path.exists():
            stats[tag]["existing"] += 1
            continue
        if limit is not None and done_now >= limit:
            stopped = "limit"
            break
        if tag not in clients:
            clients[tag] = make_client(tag)
        client = clients[tag]
        try:
            prompt = with_reminder(row["prompt"]) if reminder else row["prompt"]
            reply = client.complete(prompt, system=SYSTEM_PROMPT, repeat=repeat)
        except DailyBudgetExhausted as exc:
            stopped = f"budget: {exc}"
            break
        except ProviderError as exc:
            errors += 1
            stats[tag]["errors"] += 1
            print(f"[{tag}] {row['id']}: {exc}", file=sys.stderr)
            if errors >= MAX_CONSECUTIVE_ERRORS:
                stopped = f"too many provider errors, last: {exc}"
                break
            continue
        errors = 0
        code, status = extract_code(reply)
        record = {
            "id": f"{tag}{suffix}:{row['id']}:r{repeat}",
            "task_id": row["task_id"],
            "paraphrase_id": row["id"],
            "axis": row["axis"],
            "family": row["family"],
            "model_tag": tag + suffix,
            "provider": client.provider,
            "model_id": client.model,
            "repeat": repeat,
            "temperature": client.temperature,
            "seed": None if client.seed is None else client.seed + repeat,
            "reply": reply,
            "code": code,
            "extract_status": status,
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        stats[tag]["generated"] += 1
        stats[tag][f"extract_{status}"] += 1
        done_now += 1
    summary = {tag: dict(c) for tag, c in stats.items()}
    summary["_stopped"] = stopped
    for tag, client in clients.items():
        summary.setdefault(tag, {})["api_calls"] = client.calls
        summary[tag]["cache_hits"] = client.cache_hits
        summary[tag]["tokens"] = client.tokens_used
    return summary


def write_meta(tags: list[str], repeats: int, clients: dict) -> None:
    paraphrases = (DATA_DIR / "paraphrases.jsonl").read_bytes()
    update_run_meta(
        generation={
            "models": {
                t: {"provider": clients[t].provider, "model_id": clients[t].model} for t in clients
            },
            "temperature": TEMPERATURE,
            "seed": SEED,
            "max_tokens": next(iter(clients.values())).max_tokens if clients else None,
            "repeats": repeats,
            "system_prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest()[:16],
            "paraphrases_sha256": hashlib.sha256(paraphrases).hexdigest()[:16],
        }
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--models", required=True, help="comma list: groq,gemini,scripted")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument(
        "--tasks", default="all", help="'all', 'pilot', 'noise' or comma list of task ids"
    )
    parser.add_argument(
        "--reminder", action="store_true", help="baseline: add a one-line security reminder"
    )
    parser.add_argument("--limit", type=int, help="stop after this many new generations")
    args = parser.parse_args(argv)
    tags = args.models.split(",")
    if args.tasks == "all":
        ids = None
    elif args.tasks == "pilot":
        ids = set(pilot_task_ids())
    elif args.tasks == "noise":
        ids = set(noise_task_ids())
    else:
        ids = set(args.tasks.split(","))
    clients = {tag: make_client(tag) for tag in tags}
    summary = run(tags, args.repeats, ids, args.limit, clients=clients, reminder=args.reminder)
    if clients:
        write_meta(tags, args.repeats, clients)
    RESULTS_DIR.mkdir(exist_ok=True)
    (RESULTS_DIR / "generation_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    stopped = summary["_stopped"]
    return EXIT_BUDGET if stopped and stopped.startswith("budget") else 0


if __name__ == "__main__":
    raise SystemExit(main())
