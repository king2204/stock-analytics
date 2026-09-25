"""Run every query in business_questions.sql and print the results.

    python -m analysis.run_queries            # all queries
    python -m analysis.run_queries q6         # queries whose name starts with q6
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import duckdb
import pandas as pd

from pipelines.config import load_config

SQL_FILE = Path(__file__).with_name("business_questions.sql")


def load_queries(path: Path = SQL_FILE) -> dict[str, str]:
    """Split the file on '-- name: <id>' markers."""
    text = path.read_text()
    parts = re.split(r"^-- name: (\S+)\s*$", text, flags=re.MULTILINE)
    return {name: body.strip().rstrip(";") for name, body in zip(parts[1::2], parts[2::2])}


def run(prefix: str = "", warehouse: Path | None = None) -> dict[str, pd.DataFrame]:
    path = warehouse or load_config().warehouse_path
    results = {}
    with duckdb.connect(str(path), read_only=True) as con:
        for name, sql in load_queries().items():
            if name.startswith(prefix):
                results[name] = con.execute(sql).df()
    return results


if __name__ == "__main__":
    pd.set_option("display.width", 160)
    pd.set_option("display.max_columns", 20)
    for name, df in run(sys.argv[1] if len(sys.argv) > 1 else "").items():
        print(f"\n=== {name} ===")
        print(df.to_string(index=False))
