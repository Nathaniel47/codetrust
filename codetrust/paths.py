import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = Path(os.environ.get("CODETRUST_CACHE_DIR") or ROOT / "llm_cache")
RESULTS_DIR = Path(os.environ.get("CODETRUST_RESULTS_DIR") or ROOT / "results")
DATA_DIR = ROOT / "data"
