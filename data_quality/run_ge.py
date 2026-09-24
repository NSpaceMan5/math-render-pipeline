"""
Great Expectations runtime check against `render_events`.

Loads rows from SQLite or Postgres into a pandas DataFrame, runs the
suite defined in `great_expectations/expectations/renders_suite.json`,
prints a summary, and exits 0 (pass) or 1 (fail).

Usage:
    python data_quality/run_ge.py

Env:
    POSTGRES_DSN      — sqlite:///... or postgresql://...
    GE_SUITE_PATH     — defaults to great_expectations/expectations/renders_suite.json
"""
from __future__ import annotations
import json
import os
import sqlite3
import sys
from pathlib import Path

import pandas as pd

try:
    import great_expectations as ge
    from great_expectations.core.batch import Batch
    from great_expectations.dataset import PandasDataset
    _HAS_GE = True
except Exception as e:
    ge = None
    _HAS_GE = False
    _IMPORT_ERROR = str(e)


DEFAULT_SUITE = Path("great_expectations/expectations/renders_suite.json")


def _sqlite_path(dsn: str) -> str:
    if dsn.startswith("sqlite:///"):
        return dsn[len("sqlite:///"):]
    return dsn.replace("sqlite://", "", 1)


def _load_df(dsn: str) -> pd.DataFrame:
    if dsn.startswith("sqlite://"):
        con = sqlite3.connect(_sqlite_path(dsn))
        return pd.read_sql_query("SELECT * FROM render_events", con)
    from sqlalchemy import create_engine
    sa_dsn = dsn.replace("postgresql://", "postgresql+psycopg://", 1)
    eng = create_engine(sa_dsn)
    return pd.read_sql_query("SELECT * FROM render_events", eng)


def _apply_expectations(df: pd.DataFrame, suite: dict) -> tuple[int, list[str]]:
    """Apply a GE-style suite. We execute the same logic GE would, without
    spinning up the full DataContext — keeps CI fast and dependency-light."""
    failures: list[str] = []
    n = len(df)

    for exp in suite.get("expectations", []):
        etype = exp["expectation_type"]
        kw = exp.get("kwargs", {})
        col = kw.get("column")

        if etype == "expect_column_values_to_not_be_null":
            bad = df[col].isna().sum()
            if bad:
                failures.append(f"{etype}({col}): {bad} null(s)")
        elif etype == "expect_column_values_to_be_unique":
            bad = df[col].duplicated().sum()
            if bad:
                failures.append(f"{etype}({col}): {bad} duplicate(s)")
        elif etype == "expect_column_values_to_match_regex":
            regex = kw["regex"]
            bad = (~df[col].astype(str).str.match(regex)).sum()
            if bad:
                failures.append(f"{etype}({col}): {bad} non-matching")
        elif etype == "expect_column_values_to_be_between":
            lo = kw.get("min_value")
            hi = kw.get("max_value")
            s = pd.to_numeric(df[col], errors="coerce")
            mask = pd.Series([False] * len(s))
            if lo is not None:
                mask |= s < lo
            if hi is not None:
                mask |= s > hi
            bad = int(mask.sum())
            if bad:
                failures.append(f"{etype}({col}): {bad} out of range")
        elif etype == "expect_column_pair_values_a_to_be_greater_than_b":
            a = kw["column_A"]; b = kw["column_B"]
            eq = kw.get("or_equal", False)
            bad = ((df[a] < df[b]) if not eq else (df[a] < df[b])).sum()
            if bad:
                failures.append(f"{etype}({a},{b}): {bad} violating")
        elif etype == "expect_table_row_count_to_be_between":
            lo = kw.get("min_value", 0)
            hi = kw.get("max_value", 10**9)
            if not (lo <= n <= hi):
                failures.append(f"{etype}: row_count={n} not in [{lo},{hi}]")
        else:
            failures.append(f"unsupported expectation type: {etype}")

    return n, failures


def main() -> int:
    suite_path = Path(os.environ.get("GE_SUITE_PATH", str(DEFAULT_SUITE)))
    if not suite_path.exists():
        print(f"suite not found: {suite_path}")
        return 2

    suite = json.loads(suite_path.read_text())
    dsn = os.environ.get("POSTGRES_DSN", "sqlite:///./data/mrp.sqlite")

    try:
        df = _load_df(dsn)
    except Exception as e:
        print(f"could not load data from {dsn}: {e}")
        return 2

    n, failures = _apply_expectations(df, suite)

    print(f"suite:        {suite.get('expectation_suite_name')}")
    print(f"rows checked: {n}")
    print(f"expectations: {len(suite.get('expectations', []))}")

    if failures:
        print(f"FAILED ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        return 1

    print("ALL EXPECTATIONS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
