"""The serving layer: SQL analysis file, dashboard, and Dagster definitions."""

from pathlib import Path

import pytest

from analysis.run_queries import load_queries, run

APP = Path(__file__).resolve().parent.parent / "app.py"


def test_every_business_question_runs(built_config):
    results = run(warehouse=built_config.warehouse_path)
    assert set(results) == set(load_queries())
    assert len(results) == 10
    for name, df in results.items():
        assert not df.empty, name


def test_dashboard_renders_every_tab_without_errors(built_config, monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("WAREHOUSE_PATH", str(built_config.warehouse_path))
    monkeypatch.setenv("SOURCE", "sample")
    at = AppTest.from_file(str(APP), default_timeout=180).run()
    assert not at.exception, [e.value for e in at.exception]
    tiles = {m.label: m.value for m in at.metric}
    assert tiles["Portfolio value"].startswith("$")
    assert tiles["Last ingestion"].endswith("success")
    passed, total = tiles["dbt tests passed"].split()[-1].split("/")
    assert passed == total and int(total) >= 50
    for window in ["5Y", "1Y", "YTD"]:
        at.sidebar.radio[0].set_value(window).run()
        assert not at.exception, (window, [e.value for e in at.exception])


def test_dagster_assets_materialize_end_to_end(tmp_path, monkeypatch):
    dg = pytest.importorskip("dagster")
    from pipelines.dagster_defs import dbt_warehouse, defs, prices_are_fresh, raw_market_data

    monkeypatch.setenv("SOURCE", "sample")
    monkeypatch.setenv("WAREHOUSE_PATH", str(tmp_path / "dagster.duckdb"))
    monkeypatch.setenv("LAKE_PATH", str(tmp_path / "lake"))

    job = defs.resolve_job_def("daily_refresh")
    assert {n.name for n in job.graph.node_defs} >= {"raw_market_data", "dbt_warehouse"}
    assert defs.resolve_schedule_def("daily_refresh_schedule").cron_schedule == "30 17 * * 1-5"

    result = dg.materialize([raw_market_data, dbt_warehouse, prices_are_fresh])
    assert result.success
    meta = result.asset_materializations_for_node("raw_market_data")[0].metadata
    assert meta["status"].value == "success"


def test_failed_pipeline_run_from_dashboard_shows_error_instead_of_crashing(built_config, monkeypatch):
    from streamlit.testing.v1 import AppTest

    def failing_pipeline(cfg, **kwargs):
        raise RuntimeError("dbt build failed with exit code 1")

    monkeypatch.setenv("WAREHOUSE_PATH", str(built_config.warehouse_path))
    monkeypatch.setenv("SOURCE", "sample")
    monkeypatch.setattr("pipelines.run.run_pipeline", failing_pipeline)
    at = AppTest.from_file(str(APP), default_timeout=180).run()
    run_button = next(b for b in at.button if "Run incremental" in b.label)
    run_button.click().run()
    assert not at.exception, [e.value for e in at.exception]
    assert any("Pipeline failed" in e.value for e in at.error)


def test_dashboard_waits_while_the_warehouse_is_being_written(built_config, monkeypatch):
    """Reproduces the Streamlit Cloud first-start crash: another session holds a
    write connection in the same process. The page must wait, then load."""
    import threading

    import duckdb
    from streamlit.testing.v1 import AppTest

    monkeypatch.setenv("WAREHOUSE_PATH", str(built_config.warehouse_path))
    monkeypatch.setenv("SOURCE", "sample")
    writer = duckdb.connect(str(built_config.warehouse_path))
    threading.Timer(4.0, writer.close).start()
    at = AppTest.from_file(str(APP), default_timeout=180).run()
    assert not at.exception, [e.value for e in at.exception]
    assert any(m.label == "Portfolio value" for m in at.metric)
