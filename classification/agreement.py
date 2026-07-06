"""Inter-rater agreement and kappa metrics.

Operational gate (human review):
    needs_human_review_after_reviewer() — max(kappa_rev, coder) < threshold

Methodological reporting:
    compute_global_theme_kappa() — label-wise Cohen's kappa across dataset
    summarize_operational_rates() — agreement / reviewer / human queue rates

See classification/METHODOLOGY.md for paper-writing guidance.
"""

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from classification.constants import (
    KAPPA_HUMAN_THRESHOLD,
    THEME_FLAG_COLUMNS,
)
from classification.schema import CommentAnalysis, theme_codes_from_flags, theme_flags_vector


def theme_sets_equal(a: CommentAnalysis, b: CommentAnalysis) -> bool:
    return theme_codes_from_flags(a) == theme_codes_from_flags(b)


def per_comment_kappa(rater_x: list[bool], rater_y: list[bool]) -> float:
    """Cohen's kappa over the five binary C1–C5 flags for one comment."""
    if rater_x == rater_y:
        return 1.0
    kappa = cohen_kappa_score(rater_x, rater_y)
    if pd.isna(kappa):
        return 1.0
    return float(kappa)


def needs_human_review_after_reviewer(
    reviewer: CommentAnalysis,
    coder_a: CommentAnalysis,
    coder_b: CommentAnalysis,
    *,
    threshold: float = KAPPA_HUMAN_THRESHOLD,
) -> tuple[bool, float, float]:
    """Flag human review only when the reviewer aligns with neither coder.

    When A≠B, the reviewer often agrees with one coder and not the other.
    Using min(κ) would send every adjudicated row to humans. We require
    max(κ_rev_a, κ_rev_b) < threshold — i.e. the reviewer does not
    substantially match either original coding.
    """
    rev = theme_flags_vector(reviewer)
    kappa_a = per_comment_kappa(rev, theme_flags_vector(coder_a))
    kappa_b = per_comment_kappa(rev, theme_flags_vector(coder_b))
    needs_human = max(kappa_a, kappa_b) < threshold
    return needs_human, kappa_a, kappa_b


def compute_global_theme_kappa(
    df: pd.DataFrame,
    suffix_x: str,
    suffix_y: str,
) -> pd.DataFrame:
    """Label-wise Cohen's kappa between two raters across the dataset."""
    rows = []
    for label in THEME_FLAG_COLUMNS:
        col_x = f"{label}_{suffix_x}" if suffix_x else label
        col_y = f"{label}_{suffix_y}" if suffix_y else label
        if col_x not in df.columns or col_y not in df.columns:
            continue
        x = df[col_x].fillna(False).astype(int)
        y = df[col_y].fillna(False).astype(int)
        kappa = cohen_kappa_score(x, y)
        rows.append(
            {
                "theme": label,
                "kappa": float(kappa) if not pd.isna(kappa) else None,
                "pair": f"{suffix_x or 'final'}-{suffix_y or 'final'}",
            }
        )
    return pd.DataFrame(rows)


def summarize_operational_rates(df: pd.DataFrame) -> pd.Series:
    llm_mask = df["classification_source"].isin(["llm_agreed", "llm_reviewer"])
    llm = df.loc[llm_mask]
    n_llm = len(llm)
    if n_llm == 0:
        return pd.Series(dtype=float)

    agreed = llm["coder_agreement"].sum()
    reviewed = llm["reviewer_used"].sum()
    human = llm["needs_human_review"].sum()

    return pd.Series(
        {
            "exact_set_agreement_rate": agreed / n_llm,
            "reviewer_invocation_rate": reviewed / n_llm,
            "human_queue_rate": human / n_llm,
        }
    )
