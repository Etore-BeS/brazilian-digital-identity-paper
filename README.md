# Brazilian Digital Identity Paper

Research code for thematic classification and analysis of Instagram comments on celebrity posts.

## Repository layout

```text
classification/          Classification pipeline (rules, LLM coders, human review)
scripts/                 Runnable entry points
pipeline_extraction.ipynb  Ingestion, preprocessing, classification orchestration
analysis.ipynb           Quantitative analysis and paper figures
outputs/
  samples/               Versioned sample outputs (classification dry-run)
  aggregates/            Versioned summary tables (Table 1)
  figures/               Versioned paper figures (01–09)
  *.csv / *.xlsx         Full corpus outputs (local only; see .gitignore)
data/                    Raw scrape JSON (local only)
```

## What is versioned

- Source code, methodology dossier, sample CSVs/XLSX, aggregate tables, figures 01–09

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
