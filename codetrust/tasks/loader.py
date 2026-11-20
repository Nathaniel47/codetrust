"""Load the task set from data/tasks/<id>/."""

import json
from dataclasses import dataclass
from pathlib import Path

from codetrust.paths import DATA_DIR

TASKS_DIR = DATA_DIR / "tasks"


@dataclass(frozen=True)
class Task:
    id: str
    family: str
    cwe: str
    request: str
    short: str
    contract: list[str]
    entry: list[str]
    path: Path

    def read(self, name: str) -> str:
        return (self.path / name).read_text(encoding="utf-8")

    @property
    def contract_text(self) -> str:
        return "\n".join(f"- {line}" for line in self.contract)


def load_task(path: Path) -> Task:
    meta = json.loads((path / "task.json").read_text(encoding="utf-8"))
    return Task(path=path, **meta)


def load_tasks(root: Path = TASKS_DIR) -> list[Task]:
    return [load_task(p.parent) for p in sorted(root.glob("*/task.json"))]
