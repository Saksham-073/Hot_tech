# What's Hot on GitHub in 2026

Analysis of the 1,000 most-starred GitHub repos created in the last 365 days (snapshot: 2026-11-21).

## Top findings

Main dataset: top 300 repos per creation month (3,600 repos, Dec 2025 to 21 Nov 2026). Equal sampling per month avoids the global top-1,000's bias toward old repos.

1. **Python (992) and TypeScript (778) dominate**, then JavaScript (355) and Rust (331).
2. **AI is 58% of hot repos, not 68%.** The global top-1,000 overstated it because the very top is dominated by AI hype. AI share by month peaked at 73% in March 2026 and fell to 44-51% in Oct-Nov.
3. **Top topics:** `claude-code` (503), `ai-agents` (388), `llm` (349), `codex` (347), `ai` (299), `mcp` (290).
4. **Popularity is skewed:** median 2,514 stars, mean 6,411. AI repos have a higher median (2,846 vs 2,141).
5. **Forks grow in proportion to stars:** log-log slope 1.01, so 10x stars means about 10.3x forks (Spearman 0.76, R² 0.59). The global top-1,000 showed 1.16, an artifact of only seeing the extreme top.

| Dataset | Repos | AI share | Median stars | Fork slope |
|---|---|---|---|---|
| Monthly top-300 | 3,600 | 58% | 2,514 | 1.01 |
| Global top-1,000 | 1,000 | 68% | 8,591 | 1.16 |

## AI flag accuracy

Keyword regex in `features.py`, scored against hand labels in `data/ai_labels.csv`:

| Split | n | Precision | Recall |
|---|---|---|---|
| dev (used to tune the pattern) | 100 | 0.97 | 0.97 |
| holdout (labelled after tuning) | 60 | 0.93 | 0.93 |

Labels were assigned by an LLM (Claude) reading name, topics and description, not by a human, and borderline repos are judgment calls. Treat the numbers as indicative. Re-run with `python -m whats_hot.evaluate <snapshot.csv>`.

## Dashboard

```bash
pip install -r requirements.txt
streamlit run app.py
```

Sidebar filters (snapshot, language, AI or not, minimum stars) drive four tabs: Overview (languages, topics, stars vs forks), AI over time, Movers (needs two snapshots), Explore (searchable table with links). Chart colours come from a validated colourblind-safe palette and follow the Streamlit light/dark theme.

## Weekly tracking

Each snapshot is a dated CSV. `track.py` compares the two latest and reports:
- fastest risers (stars gained per day between snapshots, a truer momentum than stars per day since creation),
- stalled repos (lowest growth),
- new entrants, and repos that dropped out of the monthly top lists (this can just mean others overtook them).

```bash
PYTHONPATH=src python -m whats_hot --windowed          # take a snapshot
PYTHONPATH=src python -m whats_hot.track --out reports/latest.txt
```

`.github/workflows/weekly-snapshot.yml` does both every Monday and commits the CSV and report. It only runs if this folder is the root of its own GitHub repo (Actions reads `.github/` from the repo root). With the built-in token the rate limit is 30 search requests/min, so it runs with `--pause 2.5`.

## Layout

```
app.py           Streamlit dashboard
src/whats_hot/   fetch.py (API), clean.py (JSON -> DataFrame), features.py (AI flag, stats), evaluate.py (flag accuracy), track.py (snapshot diffs), load.py (read snapshots)
data/            CSV snapshots, ai_labels.csv (hand labels)
notebooks/       tutorial_original.ipynb (guided walkthrough)
tests/           pytest
```

## Run

```bash
pip install -r requirements.txt
export GITHUB_TOKEN=...            # optional, raises rate limit
PYTHONPATH=src python -m whats_hot --windowed   # top 300 per month, ~6 min without a token
PYTHONPATH=src python -m whats_hot              # global top 1,000 (original method)
PYTHONPATH=src pytest
```

## Limitations

- Still the top of the market: 300 per month, not all repos. Star thresholds differ by month (about 1,000 stars for Dec, 357 for Nov), so compare shares across months, not star counts.
- Time bias reduced, not removed: young repos have had less time to collect stars.
- AI flag is a keyword match (see accuracy above).
- Stars measure attention, not quality.
