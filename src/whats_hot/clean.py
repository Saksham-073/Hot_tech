"""Flatten raw API JSON into a clean DataFrame."""
import pandas as pd


def to_dataframe(raw_items, now=None):
    rows = [
        {
            "name": repo["full_name"],
            "description": repo.get("description"),
            "language": repo.get("language"),
            "stars": repo["stargazers_count"],
            "forks": repo["forks_count"],
            "open_issues": repo["open_issues_count"],
            "topics": repo.get("topics", []),
            "license": (repo.get("license") or {}).get("spdx_id"),
            "owner_type": repo["owner"]["type"],
            "created_at": repo["created_at"],
            "pushed_at": repo["pushed_at"],
            "url": repo["html_url"],
        }
        for repo in raw_items
    ]
    df = pd.DataFrame(rows)

    # Cleaning decisions: keep gap rows, label them; drop duplicate repos.
    df = df.drop_duplicates(subset="name").copy()
    df["language"] = df["language"].fillna("None/Docs")
    df["license"] = df["license"].fillna("No license")
    df["description"] = df["description"].fillna("")

    now = now or pd.Timestamp.now(tz="UTC")
    df["created_at"] = pd.to_datetime(df["created_at"])
    df["pushed_at"] = pd.to_datetime(df["pushed_at"])
    df["age_days"] = (now - df["created_at"]).dt.days.clip(lower=1)
    df["stars_per_day"] = df["stars"] / df["age_days"]
    df["days_since_push"] = (now - df["pushed_at"]).dt.days
    df["created_month"] = df["created_at"].dt.tz_localize(None).dt.to_period("M")
    return df.reset_index(drop=True)
