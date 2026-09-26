"""One pipeline run at a time, and readable errors when the warehouse is busy."""

import subprocess
import sys
import time

import pytest

from pipelines.ingest import connect
from pipelines.locking import WarehouseBusyError, pipeline_lock
from pipelines.run import run_pipeline
from src.warehouse import Warehouse
from tests.conftest import sample_config


def test_second_pipeline_run_is_refused_while_first_is_running(tmp_path):
    cfg = sample_config(tmp_path)
    # simulate a run in progress
    with pipeline_lock(cfg.warehouse_path), pytest.raises(WarehouseBusyError, match="already in progress"):
        run_pipeline(cfg, skip_dbt=True)
    assert run_pipeline(cfg, skip_dbt=True) == 0  # released afterwards
    assert not cfg.warehouse_path.with_suffix(".pipeline.lock").exists()


def test_stale_lock_from_crashed_run_is_cleared(tmp_path):
    cfg = sample_config(tmp_path)
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    lock = cfg.warehouse_path.with_suffix(".pipeline.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text(str(dead.pid))
    assert run_pipeline(cfg, skip_dbt=True) == 0


def test_duckdb_lock_held_by_another_process_gives_plain_message(tmp_path):
    db = tmp_path / "busy.duckdb"
    connect(db).close()
    holder = subprocess.Popen([sys.executable, "-c",
                               f"import duckdb, time; c = duckdb.connect({str(db)!r}); print('ready', flush=True); "
                               "time.sleep(30)"], stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "ready"
        with pytest.raises(WarehouseBusyError, match=f"process {holder.pid}"):
            connect(db)
        with pytest.raises(WarehouseBusyError, match="in use by another program"):
            Warehouse(db).query("select 1")
    finally:
        holder.kill()
        holder.wait()
    time.sleep(0.2)
    assert Warehouse(db).query("select 1 as x")["x"].iloc[0] == 1


def test_read_while_same_process_is_writing_is_reported_as_busy(tmp_path):
    """Streamlit serves all visitors from one process: a read-only query must not
    crash while the first-run build holds a read-write connection."""
    import duckdb

    db = tmp_path / "same.duckdb"
    writer = duckdb.connect(str(db))
    writer.execute("create table t (x int)")
    try:
        with pytest.raises(WarehouseBusyError, match="being built or updated"):
            Warehouse(db).query("select 1")
    finally:
        writer.close()
    assert Warehouse(db).query("select 1 as x")["x"].iloc[0] == 1
