"""Build anonymized public dataset for Hugging Face.

Input: outputs/classified_comments_human.csv (17,287 rows, post human review)
Output: dist/hf_dataset/{data/train.csv, data/train.parquet, table1.csv, codebook.csv}

Strips PII (raw comment, likes, timestamps) and keeps comment_anon + labels.
"""

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
INPUT_CSV = REPO_ROOT / "outputs" / "classified_comments_human.csv"
OUT_DIR = REPO_ROOT / "dist" / "hf_dataset"
DATA_DIR = OUT_DIR / "data"

# Columns to keep for public release
KEEP_COLS = [
    "hash_id",
    "case",
    "comment_anon",
    "emojis_list",
    "hashtags_list",
    "language",
    "is_brazilian",
    "comment_length",
    # final labels
    "theme_C1",
    "theme_C2",
    "theme_C3",
    "theme_C4",
    "theme_C5",
    "theme_NA",
    "theme_conf",
    "character",
    "char_conf",
    "tone",
    "tone_conf",
    "classification_source",
    "rule_id",
    "coder_agreement",
    "reviewer_used",
    "kappa_reviewer_a",
    "kappa_reviewer_b",
    "human_reviewed",
]

DROP_COLS = ["comment", "comment_norm", "likes_raw", "likes", "date_iso", "days_old"]

# columns that leak raw PII if kept — must not appear in public CSV
FORBIDDEN = set(DROP_COLS + ["username"])


def main() -> None:
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)

    # sanity: no username column should exist; if it does, drop
    for c in FORBIDDEN:
        if c in df.columns:
            print(f"Dropping PII column: {c}")

    # validate anonymization: raw comment must not leak
    if "comment" in df.columns:
        # ensure comment_anon is present
        assert "comment_anon" in df.columns, "comment_anon missing"

    # keep only allowed columns that exist
    keep = [c for c in KEEP_COLS if c in df.columns]
    missing = [c for c in KEEP_COLS if c not in df.columns]
    if missing:
        print(f"Warning: expected columns missing in input (ignored): {missing}")

    df_out = df[keep].copy()

    # anonymization checks
    anon = df_out["comment_anon"].astype(str)
    # no handle should survive except @user
    has_at = anon.str.contains("@", na=False)
    not_user = anon[has_at & ~anon.str.contains("@user", na=False)]
    if len(not_user) > 0:
        print(f"WARNING: {len(not_user)} comment_anon rows contain @ without @user — review:")
        print(not_user.head(5).to_list())
    else:
        print(f"Anonymization check OK: {has_at.sum()} rows with @, all contain @user or filtered")

    # forbidden check
    for c in FORBIDDEN:
        if c in df_out.columns:
            raise ValueError(f"Forbidden column in public output: {c}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    out_csv = DATA_DIR / "train.csv"
    df_out.to_csv(out_csv, index=False)
    print(f"Wrote {out_csv} ({len(df_out)} rows, {len(df_out.columns)} cols)")

    # parquet for HF viewer efficiency
    try:
        out_parquet = DATA_DIR / "train.parquet"
        df_out.to_parquet(out_parquet, index=False)
        print(f"Wrote {out_parquet}")
    except Exception as e:
        print(f"Parquet write skipped: {e}")

    # Table 1 aggregate (post-human)
    agg_src = REPO_ROOT / "outputs" / "aggregates" / "final_dataset_human.csv"
    if agg_src.exists():
        import shutil

        dst = OUT_DIR / "table1.csv"
        shutil.copy(agg_src, dst)
        print(f"Copied aggregate {agg_src} -> {dst}")

    # Codebook
    codebook = pd.DataFrame(
        [
            {
                "column": "hash_id",
                "type": "string",
                "description": "Anonymized ID {CASE}_{seq}, sorted by date",
            },
            {
                "column": "case",
                "type": "string",
                "description": "Case: Bruno_Mars | Fernanda_Torres | CR7",
            },
            {
                "column": "comment_anon",
                "type": "string",
                "description": "Anonymized comment text (@handle → @user)",
            },
            {
                "column": "emojis_list",
                "type": "string",
                "description": "List of emojis extracted (str repr)",
            },
            {
                "column": "hashtags_list",
                "type": "string",
                "description": "List of hashtags (str repr)",
            },
            {
                "column": "language",
                "type": "string",
                "description": "Detected language (langdetect, seed 42); empty if too short",
            },
            {
                "column": "is_brazilian",
                "type": "bool",
                "description": "Heuristic Brazilian-user flag (pt OR username OR cultural regex)",
            },
            {
                "column": "comment_length",
                "type": "int",
                "description": "Character length of comment_norm",
            },
            {"column": "theme_C1", "type": "bool", "description": "C1 Nacionalismo/Orgulho"},
            {"column": "theme_C2", "type": "bool", "description": "C2 Humor/Sátira/Meme"},
            {"column": "theme_C3", "type": "bool", "description": "C3 Conflito/Rivalidade"},
            {
                "column": "theme_C4",
                "type": "bool",
                "description": "C4 Validação/Afeto pelo Estrangeiro",
            },
            {
                "column": "theme_C5",
                "type": "bool",
                "description": "C5 Apropriação do Espaço Digital",
            },
            {"column": "theme_NA", "type": "bool", "description": "N.A. exclusive of C1–C5"},
            {
                "column": "theme_conf",
                "type": "float",
                "description": "Model self-reported confidence for theme set (0–1)",
            },
            {"column": "character", "type": "string", "description": "Afetivo | Cognitivo"},
            {"column": "char_conf", "type": "float", "description": "Confidence for character"},
            {"column": "tone", "type": "string", "description": "Positivo | Negativo | Neutro"},
            {"column": "tone_conf", "type": "float", "description": "Confidence for tone"},
            {
                "column": "classification_source",
                "type": "string",
                "description": "rule | llm_agreed | llm_reviewer | human | error",
            },
            {
                "column": "rule_id",
                "type": "string",
                "description": "Deterministic rule ID (rule rows only)",
            },
            {
                "column": "coder_agreement",
                "type": "bool",
                "description": "Coder A theme set == Coder B",
            },
            {
                "column": "reviewer_used",
                "type": "bool",
                "description": "Reviewer adjudicated (A≠B)",
            },
            {
                "column": "kappa_reviewer_a",
                "type": "float",
                "description": "Per-comment Cohen kappa reviewer↔A (when used)",
            },
            {
                "column": "kappa_reviewer_b",
                "type": "float",
                "description": "Per-comment Cohen kappa reviewer↔B (when used)",
            },
            {
                "column": "human_reviewed",
                "type": "bool",
                "description": "Post human adjudication merged",
            },
        ]
    )
    codebook_path = OUT_DIR / "codebook.csv"
    codebook.to_csv(codebook_path, index=False)
    print(f"Wrote codebook {codebook_path}")

    # Summary
    print("\nPublic dataset summary:")
    print(df_out["case"].value_counts().to_string())
    print(df_out["classification_source"].value_counts().to_string())
    n_human = int(df_out["human_reviewed"].sum()) if "human_reviewed" in df_out.columns else 0
    print(f"human_reviewed True: {n_human}")


if __name__ == "__main__":
    main()
