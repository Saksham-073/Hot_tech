"""CLI: python -m whats_hot [--windowed]  -> fetch, clean, flag, save CSV snapshot."""
import argparse
from pathlib import Path

import pandas as pd

from .clean import to_dataframe
from .features import flag_ai
from .fetch import build_query, fetch_repos, fetch_windowed

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--windowed", action="store_true",
                    help="top repos per creation month (beats the 1,000 cap, even per-month sampling)")
    ap.add_argument("--pages", type=int, default=3, help="pages per month window (100 repos each)")
    ap.add_argument("--pause", type=float, default=7,
                    help="seconds between requests (7 unauthenticated, 2.5 with a token)")
    args = ap.parse_args()

    if args.windowed:
        raw, tag = fetch_windowed(pages_per_window=args.pages, pause=args.pause), "monthly"
    else:
        query, _ = build_query()
        print("Search query:", query)
        raw, tag = fetch_repos(query, pause=args.pause), "top1000"

    df = flag_ai(to_dataframe(raw))
    DATA_DIR.mkdir(exist_ok=True)
    out = DATA_DIR / f"github_hot_repos_{tag}_{pd.Timestamp.now(tz='UTC'):%Y-%m-%d}.csv"
    df.to_csv(out, index=False)
    print(f"Saved {len(df)} repos -> {out}")


if __name__ == "__main__":
    main()
