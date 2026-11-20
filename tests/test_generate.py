import json

import pytest

from codetrust.generate import runner
from codetrust.llm.budget import DailyBudgetExhausted
from codetrust.llm.cache import ResponseCache
from codetrust.llm.client import LLMClient
from codetrust.llm.models import MODELS, SYSTEM_PROMPT, scripted_backend
from codetrust.llm.providers import ProviderError

PILOT = runner.pilot_task_ids()


def scripted_client(tmp_path, percent=30):
    return LLMClient(
        scripted_backend(percent),
        "scripted",
        "scripted",
        0.2,
        1234,
        1500,
        cache=ResponseCache(tmp_path / "cache"),
    )


class FakeClient:
    provider, model, temperature, seed, max_tokens = "p", "m", 0.2, 1, 10
    calls = cache_hits = tokens_used = 0

    def __init__(self, error):
        self.error = error

    def complete(self, *args, **kwargs):
        raise self.error


def test_pilot_is_five_tasks_from_five_families():
    assert len(PILOT) == 5
    assert len({i.split("_")[0] for i in PILOT}) == 5


def test_full_grid_size_for_one_model(tmp_path):
    out = tmp_path / "gen"
    summary = runner.run(["scripted"], out=out, clients={"scripted": scripted_client(tmp_path)})
    assert summary["scripted"]["generated"] == 500
    assert len(list(out.glob("scripted/*.json"))) == 500


def test_records_have_everything_the_scorer_needs(tmp_path):
    out = tmp_path / "gen"
    clients = {"scripted": scripted_client(tmp_path)}
    runner.run(["scripted"], task_ids={PILOT[0]}, out=out, clients=clients)
    record = json.loads(next(out.glob("scripted/*.json")).read_text(encoding="utf-8"))
    for key in (
        "id", "task_id", "paraphrase_id", "axis", "family", "model_tag", "model_id",
        "repeat", "temperature", "seed", "reply", "code", "extract_status",
    ):  # fmt: skip
        assert key in record
    assert record["extract_status"] == "ok" and record["code"].strip()


def test_rerun_skips_existing_and_makes_no_new_calls(tmp_path):
    out, client = tmp_path / "gen", scripted_client(tmp_path)
    kwargs = dict(task_ids=set(PILOT), out=out, clients={"scripted": client})
    first = runner.run(["scripted"], **kwargs)
    second = runner.run(["scripted"], **kwargs)
    assert first["scripted"]["generated"] == 50
    assert second["scripted"]["existing"] == 50 and second["scripted"]["api_calls"] == 50


def test_deleted_records_are_rebuilt_from_cache_without_new_calls(tmp_path):
    out, client = tmp_path / "gen", scripted_client(tmp_path)
    kwargs = dict(task_ids={PILOT[0]}, out=out, clients={"scripted": client})
    runner.run(["scripted"], **kwargs)
    for path in out.glob("scripted/*.json"):
        path.unlink()
    runner.run(["scripted"], **kwargs)
    assert client.calls == 10 and client.cache_hits == 10


def test_interrupted_run_covers_every_task_first(tmp_path):
    out = tmp_path / "gen"
    clients = {"scripted": scripted_client(tmp_path)}
    summary = runner.run(["scripted"], limit=50, out=out, clients=clients)
    assert summary["_stopped"] == "limit"
    assert len({p.name.split("__")[0] for p in out.glob("scripted/*.json")}) == 50


def test_repeats_make_separate_records(tmp_path):
    out = tmp_path / "gen"
    clients = {"scripted": scripted_client(tmp_path)}
    runner.run(["scripted"], repeats=2, task_ids={PILOT[0]}, out=out, clients=clients)
    assert len(list(out.glob("scripted/*.json"))) == 20


def test_budget_exhaustion_stops_cleanly(tmp_path):
    clients = {"x": FakeClient(DailyBudgetExhausted("used up"))}
    summary = runner.run(["x"], task_ids={PILOT[0]}, out=tmp_path, clients=clients)
    assert summary["_stopped"].startswith("budget")


def test_repeated_provider_errors_abort(tmp_path):
    clients = {"x": FakeClient(ProviderError("HTTP 401"))}
    summary = runner.run(["x"], out=tmp_path, clients=clients)
    assert summary["x"]["errors"] == runner.MAX_CONSECUTIVE_ERRORS
    assert "too many provider errors" in summary["_stopped"]


def test_scripted_model_hands_out_flawed_code_except_when_security_is_requested(tmp_path):
    client = scripted_client(tmp_path, percent=100)
    replies = {
        r["axis"]: client.complete(r["prompt"], system=SYSTEM_PROMPT)
        for r in runner.load_paraphrases()
        if r["task_id"] == "sqli_find_user"
    }
    assert "WHERE username = ?" in replies["mentions_security"]
    assert "WHERE username = '{username}'" in replies["canonical"]


def test_run_meta_records_models_and_settings(tmp_path, monkeypatch):
    captured = {}
    monkeypatch.setattr(runner, "update_run_meta", lambda **kw: captured.update(kw))
    runner.write_meta(["scripted"], 1, {"scripted": scripted_client(tmp_path)})
    gen = captured["generation"]
    assert gen["temperature"] == 0.2 and gen["seed"] == 1234
    assert gen["models"]["scripted"]["model_id"] == "scripted"
    assert len(gen["paraphrases_sha256"]) == 16


@pytest.mark.parametrize("tag", list(MODELS))
def test_model_ids_can_be_overridden_from_env(tag, monkeypatch):
    monkeypatch.setenv(f"CODETRUST_MODEL_{tag.upper()}", "custom-id")
    assert MODELS[tag].model_id == "custom-id"
