"""Run dual-coder classification on a stratified sample (dry-run / cost test).

Mirrors the notebook sample path (USE_SAMPLE=True) without re-running phases 1–2.
Loads pre-processed rows from classified_comments.csv, samples stratified by case,
runs classify_all_comments(), and writes:

  - classified_comments_sample.csv
  - final_dataset_sample.csv

See classification/METHODOLOGY.md for the full methodology reference.

Usage:
    uv run python run_classification_sample.py

Set USE_SAMPLE=False and OUTPUT_CSV=classified_comments.csv for a full re-run
(requires INPUT_CSV without stale classification columns).
"""

import ast
import asyncio
import os

import pandas as pd
from dotenv import load_dotenv

from classification.aggregation import generate_dataset_final, summarize_rule_coverage
from classification.agreement import compute_global_theme_kappa, summarize_operational_rates
from classification.constants import (
    KAPPA_HUMAN_THRESHOLD,
    PRICE_INPUT_TOKEN_MINI,
    PRICE_INPUT_TOKEN_NANO,
    PRICE_OUTPUT_TOKEN_MINI,
    PRICE_OUTPUT_TOKEN_NANO,
)
from classification.pipeline import classify_all_comments

USE_SAMPLE = True
SAMPLE_SIZE = 60
SAMPLE_SEED = 42
INPUT_CSV = "classified_comments.csv"
OUTPUT_CSV = "classified_comments_sample.csv"


def load_df_final(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    drop_cols = [
        "theme",
        "theme_conf",
        "character",
        "char_conf",
        "tone",
        "tone_conf",
        "needs_human_review",
        "classification_source",
    ]
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])
    for col in ("emojis_list", "hashtags_list"):
        if col in df.columns and isinstance(df[col].iloc[0], str):
            df[col] = df[col].apply(ast.literal_eval)
    return df


def make_sample(df: pd.DataFrame) -> pd.DataFrame:
    per_case = max(1, SAMPLE_SIZE // df["case"].nunique())
    parts = [
        group.sample(n=min(len(group), per_case), random_state=SAMPLE_SEED)
        for _, group in df.groupby("case", observed=True)
    ]
    return pd.concat(parts, ignore_index=True)


async def main() -> None:
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        msg = "OPENAI_API_KEY not set"
        raise RuntimeError(msg)

    df_final = load_df_final(INPUT_CSV)
    df_classify = make_sample(df_final) if USE_SAMPLE else df_final
    print(f"Sample: {len(df_classify)} comments — {df_classify['case'].value_counts().to_dict()}")

    summarize_rule_coverage(df_classify)

    res_list, metadata = await classify_all_comments(df_classify)

    results_df = pd.DataFrame(res_list)
    df_out = pd.concat([df_classify.reset_index(drop=True), results_df], axis=1)
    df_out["classification_source"] = [m.get("source") for m in metadata]
    if "human_reviewed" not in df_out.columns:
        df_out["human_reviewed"] = False

    df_out.to_csv(OUTPUT_CSV, index=False)

    input_cost = sum(
        m.get("nano_input_tokens", 0) * PRICE_INPUT_TOKEN_NANO
        + m.get("mini_input_tokens", 0) * PRICE_INPUT_TOKEN_MINI
        for m in metadata
    )
    output_cost = sum(
        m.get("nano_output_tokens", 0) * PRICE_OUTPUT_TOKEN_NANO
        + m.get("mini_output_tokens", 0) * PRICE_OUTPUT_TOKEN_MINI
        for m in metadata
    )

    print(f"\nSaved {OUTPUT_CSV} ({len(df_out)} rows)")
    print(f"Sources: {df_out['classification_source'].value_counts().to_dict()}")
    print(f"Human review queue: {int(df_out['needs_human_review'].sum())}")
    print(f"Est. cost: ${input_cost + output_cost:.4f} USD")

    llm_df = df_out[df_out["classification_source"].isin(["llm_agreed", "llm_reviewer"])]
    if len(llm_df):
        print("\nOperational rates:")
        print(summarize_operational_rates(df_out))
        print("\nKappa A↔B:")
        print(compute_global_theme_kappa(llm_df, "a", "b").to_string(index=False))

    dataset_final = generate_dataset_final(df_out)
    dataset_final.to_csv("final_dataset_sample.csv")
    print("\nSaved final_dataset_sample.csv")
    print(f"Kappa human threshold: {KAPPA_HUMAN_THRESHOLD}")


if __name__ == "__main__":
    asyncio.run(main())
