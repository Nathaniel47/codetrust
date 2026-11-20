"""Seeded dev/test split by task, stratified by vulnerability family.

The split is by task, not by prompt, so the 10 wordings of one task never end up on both sides.
Dev tasks are for choosing the extension's rules; test tasks are for reporting.
"""

import random

from codetrust.config import SEED
from codetrust.tasks.loader import Task

DEV_PER_FAMILY = 2


def make_split(tasks: list[Task], seed: int = SEED) -> dict[str, str]:
    rng = random.Random(seed)
    by_family: dict[str, list[str]] = {}
    for task in tasks:
        by_family.setdefault(task.family, []).append(task.id)
    split = {}
    for family in sorted(by_family):
        ids = sorted(by_family[family])
        rng.shuffle(ids)
        for i, task_id in enumerate(ids):
            split[task_id] = "dev" if i < DEV_PER_FAMILY else "test"
    return dict(sorted(split.items()))
