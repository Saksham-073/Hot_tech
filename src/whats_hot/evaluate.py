"""Score the keyword AI flag against hand labels (data/ai_labels.csv)."""
import ast
from pathlib import Path

import pandas as pd

from .features import flag_ai

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def score(df, labels):
    """df needs name/topics/description; labels needs name/is_ai_label. Returns precision/recall dict."""
    merged = flag_ai(df).merge(labels[["name", "is_ai_label"]], on="name")
    pred, truth = merged["is_ai"].astype(bool), merged["is_ai_label"].astype(bool)
    tp, fp, fn = (pred & truth).sum(), (pred & ~truth).sum(), (~pred & truth).sum()
    return {
        "n": len(merged),
        "precision": tp / (tp + fp) if tp + fp else float("nan"),
        "recall": tp / (tp + fn) if tp + fn else float("nan"),
        "false_pos": merged.loc[pred & ~truth, "name"].tolist(),
        "false_neg": merged.loc[~pred & truth, "name"].tolist(),
    }


def main(snapshot):
    df = pd.read_csv(snapshot)
    df["topics"] = df["topics"].apply(ast.literal_eval)
    df["description"] = df["description"].fillna("")
    labels = pd.read_csv(DATA_DIR / "ai_labels.csv")
    for split, part in labels.groupby("split"):
        r = score(df.drop(columns="is_ai", errors="ignore"), part)
        print(f"[{split}] n={r['n']} precision={r['precision']:.2f} recall={r['recall']:.2f}")
        print("  false pos:", r["false_pos"])
        print("  false neg:", r["false_neg"])


if __name__ == "__main__":
    import sys

    main(sys.argv[1])
