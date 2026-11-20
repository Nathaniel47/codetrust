from streamlit.testing.v1 import AppTest

from codetrust import dashboard_data as dd
from codetrust.paths import ROOT
from tests.test_dashboard_data import scores_frame


def test_dashboard_runs_without_errors_on_scored_data(tmp_path, monkeypatch):
    path = tmp_path / "scores.csv"
    scores_frame().to_csv(path, index=False)
    monkeypatch.setattr(dd, "SCORES", path)
    app = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=120).run()
    assert not app.exception
    assert app.title[0].value == "CodeTrust"
    assert len(app.tabs) == 5


def test_dashboard_explains_what_to_do_when_there_are_no_results(tmp_path, monkeypatch):
    monkeypatch.setattr(dd, "SCORES", tmp_path / "missing.csv")
    app = AppTest.from_file(str(ROOT / "dashboard" / "app.py"), default_timeout=60).run()
    assert not app.exception
    assert "No results yet" in app.warning[0].value
