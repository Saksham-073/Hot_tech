"""Derived columns: AI flag, topic counts, language stats."""
import pandas as pd

AI_PATTERN = (
    r"\b(?:ai|llms?|gpt|agents?|agentic|mcp|rag|claude|openai|gemini|deepseek|"
    r"machine[- ]learning|deep[- ]learning|neural|transformers?|diffusion|"
    r"chatbot|copilot|genai|generative|prompts?|ollama|"
    r"ia|codex|ocr|inference|moe)\b"
)


def flag_ai(df, pattern=AI_PATTERN):
    text = (df["topics"].apply(" ".join) + " " + df["description"]).str.lower()
    return df.assign(is_ai=text.str.contains(pattern, regex=True))


def topic_counts(df, n=20):
    return df.explode("topics")["topics"].dropna().value_counts().head(n)


def language_stats(df, min_repos=10):
    return (
        df.groupby("language")
        .agg(
            repos=("name", "count"),
            median_stars=("stars", "median"),
            median_stars_per_day=("stars_per_day", "median"),
            ai_share=("is_ai", "mean"),
        )
        .query("repos >= @min_repos")
        .sort_values("repos", ascending=False)
    )


def stars_forks_fit(df):
    """Log-log fit of forks on stars. Returns (slope, intercept, r2, spearman)."""
    import numpy as np

    fit = df[(df["forks"] > 0) & (df["stars"] > 0)]
    x, y = np.log10(fit["stars"]), np.log10(fit["forks"])
    slope, intercept = np.polyfit(x, y, 1)
    r2 = np.corrcoef(x, y)[0, 1] ** 2
    spearman = df["stars"].rank().corr(df["forks"].rank())  # Spearman = Pearson on ranks (no scipy)
    return slope, intercept, r2, spearman
