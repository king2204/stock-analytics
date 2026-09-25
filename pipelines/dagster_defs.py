"""Dagster orchestration: the same pipeline as ``python -m pipelines.run``,
split into assets so the UI shows lineage, per-step logs and retries.

    dagster dev -m pipelines.dagster_defs     # UI at http://localhost:3000

The schedule runs on weekdays at 17:30 New York time (after the US close).
"""

import dagster as dg

from pipelines.config import load_config
from pipelines.ingest import run_ingestion
from pipelines.run import run_dbt

RETRY = dg.RetryPolicy(max_retries=3, delay=60, backoff=dg.Backoff.EXPONENTIAL)


@dg.asset(group_name="extract_load", retry_policy=RETRY,
          description="Incremental load of prices, corporate actions and trades into raw.*")
def raw_market_data(context: dg.AssetExecutionContext) -> dg.MaterializeResult:
    cfg = load_config()
    result = run_ingestion(cfg)
    context.log.info(f"ingestion {result.status}: {result.rows_loaded} rows")
    if result.status == "failed":
        raise dg.Failure(f"all tickers failed: {result.tickers_failed}")
    return dg.MaterializeResult(metadata={
        "run_id": result.run_id,
        "status": result.status,
        "rows_loaded": result.rows_loaded,
        "rows_quarantined": result.rows_quarantined,
        "tickers_failed": ", ".join(result.tickers_failed) or "none",
    })


@dg.asset(group_name="transform", deps=[raw_market_data],
          description="dbt build: staging -> intermediate -> marts, plus all data tests")
def dbt_warehouse(context: dg.AssetExecutionContext) -> dg.MaterializeResult:
    cfg = load_config()
    dbt_vars = ["--vars", f"{{benchmark: {cfg.benchmark}, risk_free_rate: {cfg.risk_free_rate}}}"]
    proc = run_dbt(cfg, "build", *dbt_vars)
    summary = [line for line in proc.stdout.splitlines() if "Done. PASS=" in line]
    return dg.MaterializeResult(metadata={"dbt_summary": summary[-1].strip() if summary else "n/a"})


@dg.asset_check(asset=dbt_warehouse, description="Prices are no more than 4 days old")
def prices_are_fresh() -> dg.AssetCheckResult:
    cfg = load_config()
    proc = run_dbt(cfg, "source", "freshness", check=False)
    return dg.AssetCheckResult(passed=proc.returncode == 0,
                               severity=dg.AssetCheckSeverity.WARN,
                               metadata={"exit_code": proc.returncode})


daily_job = dg.define_asset_job("daily_refresh", selection=dg.AssetSelection.all())

daily_schedule = dg.ScheduleDefinition(
    job=daily_job,
    cron_schedule="30 17 * * 1-5",
    execution_timezone="America/New_York",
)

defs = dg.Definitions(
    assets=[raw_market_data, dbt_warehouse],
    asset_checks=[prices_are_fresh],
    jobs=[daily_job],
    schedules=[daily_schedule],
)
