"""Host side of the sandbox: start locked-down containers that test generated code.

Generated code never runs on the host. Each container gets the package, the tasks and the records
read-only, no network, a read-only root, a small tmpfs for scratch files, no capabilities and
resource limits.
"""

import json
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from codetrust.paths import RESULTS_DIR, ROOT

IMAGE = "codetrust-sandbox"
TEST_RESULTS_DIR = RESULTS_DIR / "test_results"


def docker_command(records_dir: Path, list_file: Path, image: str = IMAGE) -> list[str]:
    return [
        "docker", "run", "--rm",
        "--network", "none",
        "--read-only",
        "--tmpfs", "/tmp:rw,size=256m",
        "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges",
        "--memory", "1g",
        "--pids-limit", "256",
        "--cpus", "1",
        "--user", "1000:1000",
        # Only what the driver needs: mounting the whole repo would show generated code a .env.
        "-v", f"{ROOT / 'codetrust'}:/repo/codetrust:ro",
        "-v", f"{ROOT / 'data' / 'tasks'}:/repo/data/tasks:ro",
        "-v", f"{records_dir.resolve()}:/in:ro",
        "-v", f"{list_file.resolve()}:/list.txt:ro",
        image,
        "python", "-m", "codetrust.sandbox.driver", "--list", "/list.txt",
    ]  # fmt: skip


def container_path(path: Path, records_dir: Path) -> str:
    return "/in/" + path.relative_to(records_dir).as_posix()


def run_shard(records_dir: Path, paths: list[Path], timeout: int) -> list[dict]:
    with tempfile.TemporaryDirectory() as tmp:
        list_file = Path(tmp) / "list.txt"
        list_file.write_text(
            "\n".join(container_path(p, records_dir) for p in paths) + "\n", encoding="utf-8"
        )
        proc = subprocess.run(
            docker_command(records_dir, list_file),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    rows = [json.loads(line) for line in proc.stdout.splitlines() if line.startswith("{")]
    if proc.returncode != 0 and not rows:
        raise RuntimeError(f"sandbox container failed: {proc.stderr[-500:]}")
    return rows


def test_model(
    tag: str,
    generated_dir: Path,
    out_dir: Path = TEST_RESULTS_DIR,
    shards: int = 4,
    batch: int = 25,
    timeout: int = 3600,
) -> int:
    """Test every generation of one model that has no result yet. Returns how many were tested."""
    records_dir = (generated_dir / tag).resolve()
    out = out_dir / f"{tag}.jsonl"
    out_dir.mkdir(parents=True, exist_ok=True)
    done = (
        {json.loads(line)["id"] for line in out.read_text(encoding="utf-8").splitlines()}
        if out.exists()
        else set()
    )
    pending = []
    for path in sorted(records_dir.glob("*.json")):
        if json.loads(path.read_text(encoding="utf-8"))["id"] not in done:
            pending.append(path)
    chunks = [pending[i : i + batch] for i in range(0, len(pending), batch)]
    count = 0
    with ThreadPoolExecutor(shards) as pool, out.open("a", encoding="utf-8") as f:
        for rows in pool.map(lambda c: run_shard(records_dir, c, timeout), chunks):
            for row in rows:
                f.write(json.dumps(row) + "\n")
            f.flush()
            count += len(rows)
    return count
