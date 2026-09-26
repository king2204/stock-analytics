"""Load pipeline settings from config/pipeline.toml with env-var overrides."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "pipeline.toml"


@dataclass(frozen=True)
class Ticker:
    symbol: str
    name: str
    sector: str
    is_benchmark: bool = False


@dataclass(frozen=True)
class PipelineConfig:
    source: str
    start_date: date
    warehouse_path: Path
    lake_path: Path
    transactions_path: Path
    lookback_days: int
    benchmark: str
    risk_free_rate: float
    tickers: list[Ticker] = field(default_factory=list)

    @property
    def symbols(self) -> list[str]:
        return [t.symbol for t in self.tickers]


def _resolve(path: str) -> Path:
    p = Path(path)
    return p if p.is_absolute() else PROJECT_ROOT / p


def load_config(path: Path | str | None = None, **overrides) -> PipelineConfig:
    """Read the TOML config. Precedence: explicit overrides > env vars > file."""
    config_path = Path(path or os.environ.get("PIPELINE_CONFIG", DEFAULT_CONFIG_PATH))
    with open(config_path, "rb") as f:
        raw = tomllib.load(f)

    settings = dict(raw["pipeline"])
    for key in settings:
        env_value = os.environ.get(key.upper())
        if env_value is not None:
            settings[key] = env_value
    settings.update({k: v for k, v in overrides.items() if v is not None})

    tickers = [
        Ticker(
            symbol=t["symbol"].upper(),
            name=t.get("name", t["symbol"]),
            sector=t.get("sector", "Unknown"),
            is_benchmark=bool(t.get("is_benchmark", False)),
        )
        for t in raw.get("tickers", [])
    ]

    source = str(settings["source"]).lower()
    if source not in ("yahoo", "sample"):
        raise ValueError(f"Unknown source {source!r}; expected 'yahoo' or 'sample'")

    benchmark = str(settings["benchmark"]).upper()
    if benchmark not in {t.symbol for t in tickers}:
        raise ValueError(f"Benchmark {benchmark} must also be listed under [[tickers]]")

    return PipelineConfig(
        source=source,
        start_date=date.fromisoformat(str(settings["start_date"])),
        warehouse_path=_resolve(str(settings["warehouse_path"])),
        lake_path=_resolve(str(settings["lake_path"])),
        transactions_path=_resolve(str(settings["transactions_path"])),
        lookback_days=int(settings["lookback_days"]),
        benchmark=benchmark,
        risk_free_rate=float(settings["risk_free_rate"]),
        tickers=tickers,
    )
