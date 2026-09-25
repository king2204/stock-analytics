"""Shared fixtures. The `warehouse` fixture builds a complete warehouse from the
offline sample source once per test session (ingest + full dbt build)."""

from __future__ import annotations

from pathlib import Path

import pytest

from pipelines.config import PipelineConfig, load_config
from pipelines.run import run_pipeline


def sample_config(tmp: Path, **overrides) -> PipelineConfig:
    return load_config(source="sample", warehouse_path=str(tmp / "stocks.duckdb"),
                       lake_path=str(tmp / "lake"), **overrides)


@pytest.fixture(scope="session")
def built_config(tmp_path_factory) -> PipelineConfig:
    cfg = sample_config(tmp_path_factory.mktemp("warehouse"))
    assert run_pipeline(cfg) == 0
    return cfg


@pytest.fixture()
def con(built_config):
    import duckdb

    with duckdb.connect(str(built_config.warehouse_path), read_only=True) as c:
        yield c
