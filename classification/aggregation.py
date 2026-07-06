"""Aggregate classified comments into Tabela 1 format.

TEMA section uses multi-label presence counts (sum of binary flags per case).
CARÁTER and TOM use standard single-label crosstabs.

See classification/METHODOLOGY.md.
"""

import pandas as pd

from classification.constants import THEME_DISPLAY_NAMES


def _multilabel_theme_table(df: pd.DataFrame) -> pd.DataFrame:
    case_counts = df.groupby("case", observed=True).size()
    rows = []

    for code, display_name in THEME_DISPLAY_NAMES.items():
        if code == "NA":
            col = "theme_NA"
        else:
            col = f"theme_{code}"

        counts = df.groupby("case", observed=True)[col].sum()
        combined = pd.DataFrame(index=[display_name])

        for case in case_counts.index:
            n = int(counts.get(case, 0))
            pct = n / case_counts[case] * 100 if case_counts[case] else 0.0
            combined[f"{case}_N"] = n
            combined[f"{case}_%"] = f"{pct:.1f}%"

        combined["Total_N"] = int(counts.sum())
        rows.append(combined)

    table = pd.concat(rows)
    table.index.name = "TEMA"
    return table


def _single_label_crosstab(df: pd.DataFrame, col_name: str, section_name: str) -> pd.DataFrame:
    crosstab_n = pd.crosstab(df[col_name], df["case"], margins=True, margins_name="Total")
    crosstab_pct = pd.crosstab(df[col_name], df["case"], normalize="columns") * 100

    combined = pd.DataFrame(index=crosstab_n.index)
    for case in crosstab_n.columns:
        if case == "Total":
            combined["Total_N"] = crosstab_n["Total"]
        else:
            combined[f"{case}_N"] = crosstab_n[case]
            combined[f"{case}_%"] = crosstab_pct[case].round(1).astype(str) + "%"

    combined.index.name = section_name
    return combined


def generate_dataset_final(df: pd.DataFrame) -> pd.DataFrame:
    """Consolidate classification columns into Tabela 1 format."""
    theme_table = _multilabel_theme_table(df)
    character_table = _single_label_crosstab(df, "character", "CARÁTER")
    tone_table = _single_label_crosstab(df, "tone", "TOM (SENTIMENTO)")

    return pd.concat(
        {
            "TEMA": theme_table,
            "CARÁTER": character_table,
            "TOM (SENTIMENTO)": tone_table,
        }
    )


def summarize_rule_coverage(df: pd.DataFrame) -> pd.DataFrame:
    from classification.rules import apply_rule_based_classification

    rules = df.apply(apply_rule_based_classification, axis=1)
    covered = rules.notna()
    summary = rules[covered].map(lambda r: r["rule_id"]).value_counts().rename("n").to_frame()
    summary["pct_of_dataset"] = (summary["n"] / len(df) * 100).round(1).astype(str) + "%"

    print(f"Rule-covered comments: {covered.sum():,} / {len(df):,} ({covered.mean():.1%})")
    print(f"LLM still required: {(~covered).sum():,} ({(~covered).mean():.1%})")
    print(f"Estimated LLM cost multiplier: ~{(~covered).mean():.1%} of full-dataset baseline")
    return summary
