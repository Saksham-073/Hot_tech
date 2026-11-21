"""Download repositories from the GitHub search API."""
import os
import time
from datetime import datetime, timedelta, timezone

import requests

URL = "https://api.github.com/search/repositories"


def build_query(days=365, min_stars=50):
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    return f"created:>{since} stars:>{min_stars}", since


def make_headers(token=None):
    token = token or os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_repos(query, pages=10, pause=7, token=None):
    """Return raw repo dicts, sorted by stars. API caps at 1,000 results (10 pages)."""
    headers = make_headers(token)
    all_items = []
    for page in range(1, pages + 1):
        params = {"q": query, "sort": "stars", "order": "desc", "per_page": 100, "page": page}
        for _ in range(3):
            r = requests.get(URL, params=params, headers=headers, timeout=30)
            if r.status_code == 200:
                break
            print(f"  page {page}: status {r.status_code}, waiting 60s and retrying...")
            time.sleep(60)
        else:
            print("Giving up after 3 tries. Run again in a few minutes.")
            break

        items = r.json().get("items", [])
        if not items:
            break
        all_items.extend(items)
        print(f"page {page:2}: got {len(items)} repos (total so far: {len(all_items)})")
        time.sleep(pause)
    return all_items


def month_windows(months=12, today=None):
    """Return [(start, end)] date strings (inclusive) covering the last `months` months, oldest first."""
    today = today or datetime.now(timezone.utc).date()
    first = today.replace(day=1)
    bounds = []
    for i in range(months, -1, -1):
        y, m = first.year, first.month - i
        while m <= 0:
            y, m = y - 1, m + 12
        bounds.append(first.replace(year=y, month=m))
    windows = []
    for start, nxt in zip(bounds, bounds[1:]):
        windows.append((start.isoformat(), (nxt - timedelta(days=1)).isoformat()))
    windows.append((first.isoformat(), today.isoformat()))
    return windows[-months:] if len(windows) > months else windows


def fetch_windowed(months=12, pages_per_window=3, min_stars=50, pause=7, token=None):
    """Top repos per creation month. Equal sampling per month sidesteps the 1,000-result cap
    and the bias toward old repos that a single global top-1,000 has."""
    all_items = []
    for start, end in month_windows(months):
        query = f"created:{start}..{end} stars:>{min_stars}"
        print(f"== {start}..{end}")
        all_items.extend(fetch_repos(query, pages=pages_per_window, pause=pause, token=token))
    return all_items
