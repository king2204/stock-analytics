"""Pipeline entry point: ingest -> dbt build (models + tests) -> freshness check.

    python -m pipelines.run                      # incremental, source from config
    python -m pipelines.run --source sample      # offline synthetic data
    python -m pipelines.run --full-refresh       # re-pull everything from start_date
    python -m pipelines.run --skip-dbt           # extract/load only
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

import duckdb
import pandas as pd

from pipelines.config import PROJECT_ROOT, PipelineConfig, load_config
from pipelines.ingest import run_ingestion

log = logging.getLogger("pipeline")
DBT_DIR = PROJECT_ROOT / "dbt"


def dbt_executable() -> str:
    local = Path(sys.executable).parent / "dbt"
    return str(local) if local.exists() else (shutil.which("dbt") or "dbt")


def run_dbt(cfg: PipelineConfig, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    env = {**os.environ, "WAREHOUSE_PATH": str(cfg.warehouse_path)}
    cmd = [dbt_executable(), *args, "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)]
    log.info("running: %s", " ".join(cmd[:3]))
    proc = subprocess.run(cmd, env=env, cwd=DBT_DIR, text=True, capture_output=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if check and proc.returncode != 0:
        raise RuntimeError(f"dbt {args[0]} failed with exit code {proc.returncode}")
    return proc


def record_dbt_results(cfg: PipelineConfig, run_id: str) -> None:
    """Persist the outcome of every dbt node into meta.dbt_results so data-quality
    history lives in the warehouse (dbt's target/ folder is overwritten each run)."""
    path = DBT_DIR / "target" / "run_results.json"
    if not path.exists():
        return
    data = json.loads(path.read_text())
    rows = [{
        "run_id": run_id,
        "generated_at": data.get("metadata", {}).get("generated_at"),
        "unique_id": r["unique_id"],
        "resource_type": r["unique_id"].split(".")[0],
        "name": r["unique_id"].split(".")[2],
        "status": r["status"],
        "failures": r.get("failures"),
        "execution_time": r.get("execution_time"),
        "message": (r.get("message") or "")[:500],
    } for r in data.get("results", [])]
    if not rows:
        return
    with duckdb.connect(str(cfg.warehouse_path)) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS meta.dbt_results (
            run_id VARCHAR, generated_at VARCHAR, unique_id VARCHAR, resource_type VARCHAR, name VARCHAR,
            status VARCHAR, failures INTEGER, execution_time DOUBLE, message VARCHAR)""")
        con.register("incoming", pd.DataFrame(rows))
        con.execute("INSERT INTO meta.dbt_results SELECT * FROM incoming")


def run_pipeline(cfg: PipelineConfig, full_refresh: bool = False, skip_dbt: bool = False,
                 symbols: list[str] | None = None) -> int:
    result = run_ingestion(cfg, symbols=symbols, full_refresh=full_refresh)
    log.info("ingestion %s: run_id=%s rows=%d quarantined=%d failed=%s", result.status, result.run_id,
             result.rows_loaded, result.rows_quarantined, list(result.tickers_failed) or "none")
    if result.status == "failed":
        return 1
    if skip_dbt:
        return 0

    dbt_vars = ["--vars", f"{{benchmark: {cfg.benchmark}, risk_free_rate: {cfg.risk_free_rate}}}"]
    build = run_dbt(cfg, "build", *dbt_vars, check=False)
    record_dbt_results(cfg, result.run_id)
    if build.returncode != 0:
        raise RuntimeError(f"dbt build failed with exit code {build.returncode}")
    # Freshness is a warning signal (weekends/holidays), so it never fails the run.
    run_dbt(cfg, "source", "freshness", *dbt_vars, check=False)
    return 0 if result.status == "success" else 2


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", choices=["yahoo", "sample"], help="override config source")
    parser.add_argument("--full-refresh", action="store_true", help="ignore watermarks and reload history")
    parser.add_argument("--skip-dbt", action="store_true", help="only extract and load")
    parser.add_argument("--tickers", nargs="+", help="subset of tickers to ingest")
    parser.add_argument("--config", help="path to pipeline.toml")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = load_config(args.config, source=args.source)
    try:
        return run_pipeline(cfg, full_refresh=args.full_refresh, skip_dbt=args.skip_dbt, symbols=args.tickers)
    except Exception as exc:
        log.error("pipeline failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
