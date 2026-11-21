"""Load saved snapshot CSVs back into DataFrames."""
import ast

import pandas as pd

from .track import DATA_DIR, latest_snapshots, snapshot_date


def read_snapshot(path):
    df = pd.read_csv(path)
    df["topics"] = df["topics"].apply(ast.literal_eval)
    df["description"] = df["description"].fillna("")
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)
    df["pushed_at"] = pd.to_datetime(df["pushed_at"], utc=True)
    return df


def list_snapshots(kind="monthly", data_dir=DATA_DIR):
    """[(date, path)] newest first."""
    return [(snapshot_date(p), p) for p in reversed(latest_snapshots(kind, data_dir))]
