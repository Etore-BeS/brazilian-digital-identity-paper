"""Reprocess rows that failed during LLM classification (classification_source=error).

Loads OPENAI_API_KEY from .env (unlike ad-hoc python -c snippets).

Usage:
    uv run python scripts/reprocess_classification_errors.py

Optional env vars:
    SEMAPHORE_LIMIT=5   parallel API cap (default 5)
    INPUT_CSV=outputs/classified_comments.csv
"""

import ast
import asyncio
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from classification.constants import (
    CLASSIFICATION_COLUMNS,
    KAPPA_HUMAN_THRESHOLD,
    THEME_COLUMNS_A,
    THEME_COLUMNS_B,
    THEME_COLUMNS_HUMAN_MAIN,
)
from classification.human_review import export_human_review_queue, initialize_human_columns
from classification.pipeline import classify_all_comments

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUTS = REPO_ROOT / "outputs"
INPUT_CSV = Path(os.getenv("INPUT_CSV", str(OUTPUTS / "classified_comments.csv")))
SEMAPHORE_LIMIT = int(os.getenv("SEMAPHORE_LIMIT", "5"))

STRIP_COLUMNS = [
    "theme",
    *CLASSIFICATION_COLUMNS,
    "rule_id",
    "classification_source",
    *THEME_COLUMNS_A,
    *THEME_COLUMNS_B,
    "character_a",
    "tone_a",
    "confidence_a",
    "character_b",
    "tone_b",
    "confidence_b",
    *THEME_COLUMNS_HUMAN_MAIN,
    "character_human",
    "tone_human",
    "human_notes",
    "reviewed_by",
    "reviewed_at",
    "human_reviewed",
]


def load_classified(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    for col in ("emojis_list", "hashtags_list"):
        if col in df.columns and len(df) and isinstance(df[col].iloc[0], str):
            df[col] = df[col].apply(ast.literal_eval)
    return df


def apply_human_review_gate(df: pd.DataFrame) -> pd.DataFrame:
    """Human queue = reviewer adjudicated + low kappa. Errors are not human review."""
    out = df.copy()
    max_kappa = out[["kappa_reviewer_a", "kappa_reviewer_b"]].max(axis=1)
    out.loc[out["classification_source"] == "error", "needs_human_review"] = False
    out["needs_human_review"] = out["reviewer_used"].fillna(False).astype(bool) & (
        max_kappa < KAPPA_HUMAN_THRESHOLD
    )
    return out


async def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    if not os.getenv("OPENAI_API_KEY"):
        msg = "OPENAI_API_KEY not set — ensure .env exists in project root"
        raise RuntimeError(msg)

    df = load_classified(INPUT_CSV)
    errors = df["classification_source"] == "error"
    n_errors = int(errors.sum())
    if n_errors == 0:
        print("No error rows to reprocess.")
        return

    retry_df = df.loc[errors].drop(
        columns=[c for c in STRIP_COLUMNS if c in df.columns],
        errors="ignore",
    )
    print(f"Reprocessing {n_errors:,} error rows (semaphore={SEMAPHORE_LIMIT})...")

    res_list, metadata = await classify_all_comments(retry_df, semaphore_limit=SEMAPHORE_LIMIT)

    results = pd.DataFrame(res_list)
    retry_out = pd.concat([retry_df.reset_index(drop=True), results], axis=1)
    retry_out["classification_source"] = [m.get("source") for m in metadata]

    merged = pd.concat([df.loc[~errors], retry_out], ignore_index=True)
    merged = initialize_human_columns(merged)
    merged = apply_human_review_gate(merged)
    merged.to_csv(INPUT_CSV, index=False)

    still_err = int((merged["classification_source"] == "error").sum())
    n_human = int(merged["needs_human_review"].sum())
    print(f"\nSaved {INPUT_CSV}")
    print(f"Errors remaining: {still_err:,}")
    print(f"Human review queue (real): {n_human:,}")
    print("\nSources:")
    print(merged["classification_source"].value_counts().to_string())

    queue_csv = OUTPUTS / "human_review_queue.csv"
    queue_xlsx = OUTPUTS / "human_review_queue.xlsx"
    export_human_review_queue(merged, str(queue_csv), str(queue_xlsx))
    print(f"\nExported {queue_csv} and {queue_xlsx}")


if __name__ == "__main__":
    asyncio.run(main())
