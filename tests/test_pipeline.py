import pandas as pd

from whats_hot.clean import to_dataframe
from whats_hot.features import flag_ai, topic_counts


def _repo(name, **kw):
    base = {
        "full_name": name, "description": None, "language": None,
        "stargazers_count": 100, "forks_count": 10, "open_issues_count": 1,
        "topics": [], "license": None, "owner": {"type": "User"},
        "created_at": "2026-10-01T00:00:00Z", "pushed_at": "2026-11-01T00:00:00Z",
        "html_url": f"https://github.com/{name}",
    }
    return {**base, **kw}


def test_clean_fills_gaps_and_dedupes():
    raw = [_repo("a/x"), _repo("a/x"), _repo("b/y", language="Python", license={"spdx_id": "MIT"})]
    df = to_dataframe(raw, now=pd.Timestamp("2026-11-21", tz="UTC"))
    assert len(df) == 2
    assert df.loc[0, "language"] == "None/Docs"
    assert df.loc[0, "license"] == "No license"
    assert df.loc[0, "description"] == ""
    assert df.loc[1, "license"] == "MIT"
    assert df["age_days"].min() >= 1


def test_ai_flag_word_boundary():
    raw = [
        _repo("a/ai", topics=["llm"], description="An agent framework"),
        _repo("b/mail", description="said email client"),
    ]
    df = flag_ai(to_dataframe(raw))
    assert df.set_index("name")["is_ai"].to_dict() == {"a/ai": True, "b/mail": False}


def test_topic_counts():
    df = to_dataframe([_repo("a/x", topics=["ai", "rust"]), _repo("b/y", topics=["ai"])])
    assert topic_counts(df).to_dict() == {"ai": 2, "rust": 1}


def test_month_windows_cover_contiguous_months():
    from datetime import date, timedelta

    from whats_hot.fetch import month_windows

    w = month_windows(12, today=date(2026, 11, 21))
    assert len(w) == 12
    assert w[0][0] == "2025-12-01" and w[-1] == ("2026-11-01", "2026-11-21")
    assert w[2] == ("2026-02-01", "2026-02-28")
    for (_, end), (start, _) in zip(w, w[1:]):
        assert date.fromisoformat(start) - date.fromisoformat(end) == timedelta(days=1)


def test_ai_flag_scores_against_labels():
    from whats_hot.evaluate import score

    df = to_dataframe([_repo("a/ai", topics=["llm"]), _repo("b/web", description="a web server")])
    labels = pd.DataFrame({"name": ["a/ai", "b/web"], "is_ai_label": [1, 0]})
    r = score(df, labels)
    assert r["precision"] == 1 and r["recall"] == 1


def test_compare_statuses_and_gain():
    from whats_hot.track import compare

    def snap(rows):
        return pd.DataFrame(rows, columns=["name", "stars", "forks", "language", "is_ai", "description"])

    old = snap([["a", 100, 5, "Go", True, ""], ["gone", 50, 1, "Go", False, ""]])
    new = snap([["a", 170, 9, "Go", True, ""], ["fresh", 80, 2, "Rust", False, ""]])
    c = compare(old, new, days=7).set_index("name")
    assert c.loc["a", "status"] == "continuing" and c.loc["a", "star_gain"] == 70
    assert c.loc["a", "gain_per_day"] == 10 and c.loc["a", "growth_pct"] == 70
    assert c.loc["fresh", "status"] == "new" and c.loc["gone", "status"] == "dropped"


def test_latest_snapshots_sorted_by_date(tmp_path):
    from whats_hot.track import latest_snapshots

    for d in ["2026-12-05", "2026-11-21", "2026-11-28"]:
        (tmp_path / f"github_hot_repos_monthly_{d}.csv").write_text("x")
    (tmp_path / "github_hot_repos_top1000_2026-11-21.csv").write_text("x")
    names = [p.name[-14:-4] for p in latest_snapshots("monthly", tmp_path)]
    assert names == ["2026-11-21", "2026-11-28", "2026-12-05"]
