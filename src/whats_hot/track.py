"""Compare two snapshots: who is rising, who is new, who fell out of the monthly top lists."""
import argparse
import re
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})\.csv$")


def snapshot_date(path):
    return pd.Timestamp(DATE_RE.search(str(path)).group(1))


def latest_snapshots(kind="monthly", data_dir=DATA_DIR):
    """Return snapshot paths for `kind`, oldest first."""
    return sorted(data_dir.glob(f"github_hot_repos_{kind}_*.csv"), key=snapshot_date)


def compare(old, new, days):
    """Per-repo change between two snapshots `days` apart.

    status: 'new' (only in new), 'dropped' (only in old; may just mean others overtook it,
    not that it stopped growing), 'continuing' (in both).
    """
    m = old[["name", "stars", "forks"]].merge(
        new[["name", "stars", "forks", "language", "is_ai", "description"]],
        on="name", how="outer", suffixes=("_old", ""), indicator=True,
    )
    m["status"] = m["_merge"].map({"left_only": "dropped", "right_only": "new", "both": "continuing"})
    m = m.drop(columns="_merge").rename(columns={"stars": "stars_new", "forks": "forks_new"})
    m["star_gain"] = m["stars_new"] - m["stars_old"]
    m["gain_per_day"] = m["star_gain"] / max(days, 1)
    m["growth_pct"] = m["star_gain"] / m["stars_old"] * 100
    return m


def report(old, new, days, top=10):
    """Plain-text summary of risers, stalled repos, new entrants and dropped repos."""
    c = compare(old, new, days)
    cont = c[c["status"] == "continuing"]
    cols = ["name", "stars_old", "stars_new", "gain_per_day", "growth_pct"]
    lines = [f"Compared snapshots {days} days apart: {len(cont)} repos in both, "
             f"{(c.status == 'new').sum()} new, {(c.status == 'dropped').sum()} dropped.", ""]
    lines += ["Fastest risers (stars/day since last snapshot):",
              cont.nlargest(top, "gain_per_day")[cols].round(1).to_string(index=False), ""]
    lines += ["Stalled (lowest growth %):",
              cont.nsmallest(top, "growth_pct")[cols].round(1).to_string(index=False), ""]
    lines += ["Biggest new entrants:",
              c[c.status == "new"].nlargest(top, "stars_new")[["name", "stars_new", "language"]]
              .to_string(index=False), ""]
    lines += ["Dropped out (most stars at last sight):",
              c[c.status == "dropped"].nlargest(top, "stars_old")[["name", "stars_old"]]
              .to_string(index=False)]
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", default="monthly", choices=["monthly", "top1000"])
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--out", help="also write the report to this file")
    args = ap.parse_args()

    paths = latest_snapshots(args.kind)
    if len(paths) < 2:
        print(f"Need at least 2 '{args.kind}' snapshots in {DATA_DIR}, found {len(paths)}.")
        return
    old_p, new_p = paths[-2], paths[-1]
    days = (snapshot_date(new_p) - snapshot_date(old_p)).days
    text = report(pd.read_csv(old_p), pd.read_csv(new_p), days, args.top)
    print(f"{old_p.name} -> {new_p.name}\n")
    print(text)
    if args.out:
        Path(args.out).write_text(f"{old_p.name} -> {new_p.name}\n\n{text}\n")


if __name__ == "__main__":
    main()
