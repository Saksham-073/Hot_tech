"""Streamlit dashboard: streamlit run app.py"""
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

from whats_hot.features import stars_forks_fit  # noqa: E402
from whats_hot.load import list_snapshots, read_snapshot  # noqa: E402
from whats_hot.track import compare  # noqa: E402

st.set_page_config(page_title="What's hot on GitHub", page_icon=":chart_with_upwards_trend:", layout="wide")

# Validated categorical slots 1-2 (blue, orange) from the dataviz reference palette.
try:
    DARK = st.context.theme.type == "dark"
except Exception:
    DARK = False
BLUE = "#3987e5" if DARK else "#2a78d6"
ORANGE = "#d95926" if DARK else "#eb6834"
INK = "#f0efec" if DARK else "#0b0b0b"
MUTED = "#c3c2b7" if DARK else "#52514e"
GRID = "#3a3a38" if DARK else "#e6e5e1"


def style(chart):
    return (chart.configure_axis(labelColor=MUTED, titleColor=MUTED, gridColor=GRID, domainColor=GRID, tickColor=GRID)
            .configure_legend(labelColor=MUTED, titleColor=MUTED)
            .configure_view(stroke=None))


@st.cache_data
def load(path):
    return read_snapshot(path)


snaps = list_snapshots("monthly")
if not snaps:
    st.error("No monthly snapshots in data/. Run: PYTHONPATH=src python -m whats_hot --windowed")
    st.stop()

st.title("What's hot on GitHub")

with st.sidebar:
    st.header("Filters")
    snap_date = st.selectbox("Snapshot", [d for d, _ in snaps], format_func=lambda d: d.strftime("%Y-%m-%d"))
    path = dict(snaps)[snap_date]
    full = load(path)
    langs = full["language"].value_counts().index.tolist()
    sel_langs = st.multiselect("Language", langs, placeholder="All languages")
    ai_mode = st.radio("Repo type", ["All", "AI-related", "Not AI"], horizontal=True)
    min_stars = st.slider("Minimum stars", 0, int(full["stars"].quantile(0.95)), 0, step=100)
    st.caption("AI flag is a keyword match (precision and recall about 0.93 on a hand-labelled holdout).")

df = full
if sel_langs:
    df = df[df["language"].isin(sel_langs)]
if ai_mode != "All":
    df = df[df["is_ai"] == (ai_mode == "AI-related")]
df = df[df["stars"] >= min_stars]

if df.empty:
    st.warning("No repos match these filters.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Repos", f"{len(df):,}")
c2.metric("AI share", f"{df['is_ai'].mean() * 100:.0f}%")
c3.metric("Median stars", f"{df['stars'].median():,.0f}")
c4.metric("Top language", df["language"].value_counts().index[0])

tab_over, tab_ai, tab_movers, tab_explore = st.tabs(["Overview", "AI over time", "Movers", "Explore"])

with tab_over:
    left, right = st.columns(2)
    lang = df["language"].value_counts().head(12).rename_axis("language").reset_index(name="repos")
    left.subheader("Repos by language")
    left.altair_chart(style(
        alt.Chart(lang).mark_bar(color=BLUE, cornerRadiusEnd=4, size=14).encode(
            y=alt.Y("language:N", sort="-x", title=None),
            x=alt.X("repos:Q", title="Repos"),
            tooltip=["language", "repos"],
        ).properties(height=330)), theme=None, width="stretch")

    topics = df.explode("topics")["topics"].dropna().value_counts().head(15).rename_axis("topic").reset_index(name="repos")
    right.subheader("Most common topics")
    right.altair_chart(style(
        alt.Chart(topics).mark_bar(color=BLUE, cornerRadiusEnd=4, size=10).encode(
            y=alt.Y("topic:N", sort="-x", title=None),
            x=alt.X("repos:Q", title="Repos"),
            tooltip=["topic", "repos"],
        ).properties(height=330)), theme=None, width="stretch")

    st.subheader("Stars vs forks")
    slope, _, r2, rho = stars_forks_fit(df) if len(df) > 2 else (float("nan"),) * 4
    st.caption(f"Log-log slope {slope:.2f}: 10x the stars goes with about {10 ** slope:.1f}x the forks "
               f"(Spearman {rho:.2f}, R² {r2:.2f}).")
    sc = df[(df["forks"] > 0) & (df["stars"] > 0)].assign(type=lambda d: d["is_ai"].map({True: "AI", False: "Not AI"}))
    st.altair_chart(style(
        alt.Chart(sc).mark_circle(size=28, opacity=0.5).encode(
            x=alt.X("stars:Q", scale=alt.Scale(type="log"), title="Stars (log)"),
            y=alt.Y("forks:Q", scale=alt.Scale(type="log"), title="Forks (log)"),
            color=alt.Color("type:N", scale=alt.Scale(domain=["AI", "Not AI"], range=[BLUE, ORANGE]), title=None),
            tooltip=["name", "stars", "forks", "language"],
        ).properties(height=380)), theme=None, width="stretch")

with tab_ai:
    st.subheader("AI share of each month's top repos")
    st.caption("Each month is the 300 most-starred repos created that month, so shares are comparable. "
               "The newest month is partial.")
    # Uses the unfiltered-by-AI frame so the share stays meaningful; language/min-stars filters still apply.
    base = full
    if sel_langs:
        base = base[base["language"].isin(sel_langs)]
    base = base[base["stars"] >= min_stars]
    m = (base.assign(month=base["created_at"].dt.tz_localize(None).dt.to_period("M").dt.to_timestamp())
         .groupby("month").agg(share=("is_ai", "mean"), repos=("name", "count")).reset_index())
    line = alt.Chart(m).mark_line(color=BLUE, strokeWidth=2, point=alt.OverlayMarkDef(color=BLUE, size=60)).encode(
        x=alt.X("month:T", title=None, axis=alt.Axis(format="%b %Y")),
        y=alt.Y("share:Q", title="AI share", axis=alt.Axis(format="%"), scale=alt.Scale(domain=[0, 1])),
        tooltip=[alt.Tooltip("month:T", format="%b %Y"), alt.Tooltip("share:Q", format=".0%"), "repos"],
    ).properties(height=360)
    st.altair_chart(style(line), theme=None, width="stretch")

with tab_movers:
    older = [(d, p) for d, p in snaps if d < snap_date]
    if not older:
        st.info("Movers compare two snapshots, and there is only one so far. Take another snapshot next week "
                "(PYTHONPATH=src python -m whats_hot --windowed) and this tab fills in.")
        st.subheader("Meanwhile: fastest since creation")
        st.dataframe(df.nlargest(15, "stars_per_day")[["name", "language", "stars", "age_days", "stars_per_day"]]
                     .round(1), hide_index=True, width="stretch")
    else:
        prev_date, prev_path = older[0]
        days = (snap_date - prev_date).days
        c = compare(load(prev_path), full, days)
        st.caption(f"Change since {prev_date:%Y-%m-%d} ({days} days).")
        cont = c[c["status"] == "continuing"]
        cols = ["name", "language", "stars_old", "stars_new", "gain_per_day", "growth_pct"]
        a, b = st.columns(2)
        a.subheader("Fastest risers")
        a.dataframe(cont.nlargest(15, "gain_per_day")[cols].round(1), hide_index=True, width="stretch")
        b.subheader("Stalled")
        b.dataframe(cont.nsmallest(15, "growth_pct")[cols].round(1), hide_index=True, width="stretch")
        st.subheader("New entrants")
        st.dataframe(c[c.status == "new"].nlargest(15, "stars_new")[["name", "language", "stars_new"]],
                     hide_index=True, width="stretch")
        st.caption("Dropped repos may just have been overtaken inside their month's top 300.")

with tab_explore:
    st.subheader("All matching repos")
    q = st.text_input("Search name or description")
    view = df
    if q:
        mask = view["name"].str.contains(q, case=False, regex=False) | view["description"].str.contains(q, case=False, regex=False)
        view = view[mask]
    st.dataframe(
        view.sort_values("stars", ascending=False)[["name", "language", "stars", "forks", "is_ai", "description", "url"]],
        hide_index=True, width="stretch",
        column_config={"url": st.column_config.LinkColumn("link", display_text="open"),
                       "is_ai": st.column_config.CheckboxColumn("AI")},
    )
    st.caption(f"{len(view):,} repos")
