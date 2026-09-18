# Brazilian Digital Identity Paper

[![HF Dataset](https://img.shields.io/badge/%F0%9F%A4%97_Dataset-Hugging_Face-yellow)](https://huggingface.co/datasets/Etore-BeS/brazilian-digital-identity-instagram-corpus)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Dataset: CC BY 4.0](https://img.shields.io/badge/Dataset-CC%20BY%204.0-blue.svg)](LICENSE-DATA.md)

Research code and anonymized thematic corpus (17,287 Instagram comments) for the study of Brazilian digital identity. Three cases: Bruno Mars (8,100), Fernanda Torres / Oscar 2025 (6,619), Cristiano Ronaldo tribute to Pelé (2,568). Related TCC: *O comportamento digital dos brasileiros nas redes sociais e sua influência na construção da imagem do Brasil no exterior: uma análise netnográfica* (Sá, P. F., USP FEA-RP).

## Data Availability

- **Dataset (anonymized, CC BY 4.0):** https://huggingface.co/datasets/Etore-BeS/brazilian-digital-identity-instagram-corpus — `comment_anon` only (`@handle` → `@user`, usernames removed), version 1.0.0, collection March 7–11, 2026. See `dist/hf_dataset/` (built via `scripts/prepare_public_dataset.py` from `outputs/classified_comments_human.csv`).
- **Aggregates:** `outputs/aggregates/final_dataset_human.csv` (Table 1) + `dist/hf_dataset/table1.csv`
- **Raw scrape JSON:** `data/` (local only, not published)

## How to Cite

Cite **both** the dataset and the software (two entries). After the Zenodo release, replace `XXXXXXX` with the real DOI.

```bibtex
@dataset{braga_santos_sa_2026_brazilian_identity,
  title     = {Brazilian Digital Identity on Instagram — Thematic Corpus (17,287 anonymized comments)},
  author    = {Braga e Santos, Étore and Sá, Pâmella Fernandes de},
  year      = {2026},
  publisher = {Hugging Face},
  url       = {https://huggingface.co/datasets/Etore-BeS/brazilian-digital-identity-instagram-corpus},
  doi       = {10.5281/zenodo.XXXXXXX},
  license   = {CC BY 4.0},
  version   = {1.0.0}
}
@software{braga_santos_sa_2026_code,
  title     = {Brazilian Digital Identity on Instagram — Code and Thematic Corpus},
  author    = {Braga e Santos, Étore and Sá, Pâmella Fernandes de},
  year      = {2026},
  url       = {https://github.com/Etore-BeS/brazilian-digital-identity-paper},
  doi       = {10.5281/zenodo.XXXXXXX},
  license   = {MIT},
  version   = {1.0.0}
}
```

Also see `CITATION.cff` (GitHub citation widget) and `.zenodo.json`.

## Repository layout

```text
classification/          Classification pipeline (rules, LLM coders, human review)
scripts/                 Runnable entry points
  prepare_public_dataset.py  Build anonymized HF dataset (dist/hf_dataset/)
pipeline_extraction.ipynb  Ingestion, preprocessing, classification orchestration
analysis.ipynb           Quantitative analysis and paper figures
outputs/
  samples/               Versioned sample outputs (classification dry-run)
  aggregates/            Versioned summary tables (Table 1)
  figures/en/            English paper figures (01–09)
  figures/pt/            Portuguese paper figures (01–09)
  *.csv / *.xlsx         Full corpus outputs (local only; see .gitignore)
data/                    Raw scrape JSON (local only)
dist/hf_dataset/         Publishable HF dataset (generated, not raw)
  data/train.csv         Anonymized corpus (17,287 rows)
  codebook.csv           Column definitions
  table1.csv             Aggregated Table 1
  README.md              HF dataset card (EN + PT)
```

## What is versioned

- Source code, methodology dossier, sample CSVs/XLSX, aggregate tables, figures 01–09
- `dist/hf_dataset/` is generated; commit it before a release tag

## What stays local

- `data/` raw comments
- Full classified corpora (`outputs/classified_comments*.csv`)
- Human review queues for the full run (`outputs/human_review_queue*`)
- `.env` with API keys

## Setup

```bash
# bash / fish
uv sync
cp .env.example .env   # if you add one; otherwise create .env with OPENAI_API_KEY
```

Place raw JSON under `data/` and run `pipeline_extraction.ipynb` from the repo root.

## Build public dataset

```bash
uv run python scripts/prepare_public_dataset.py
# writes dist/hf_dataset/data/train.csv (26 cols, no PII) + codebook + table1
```

## Run classification sample

```bash
# bash / fish
uv run python scripts/run_classification_sample.py
```

Writes to `outputs/samples/` when `USE_SAMPLE=True` in the script. See `classification/METHODOLOGY.md` for the full procedure.

## Reprocess API errors

```bash
# bash / fish
uv run python scripts/reprocess_classification_errors.py
```

## Lint

```bash
# bash / fish
uv run ruff check .
uv run ruff format --check .
```

## Licenses

- **Code:** MIT (`LICENSE`)
- **Dataset:** CC BY 4.0 (`LICENSE-DATA.md`, `dist/hf_dataset/README.md`)
