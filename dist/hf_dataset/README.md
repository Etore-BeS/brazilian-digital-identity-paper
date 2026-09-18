---
language:
  - pt
  - en
license: cc-by-4.0
task_categories:
  - text-classification
tags:
  - brazilian-identity
  - social-identity-theory
  - netnography
  - instagram
  - content-analysis
  - llm-annotation
  - thematic-coding
size_categories:
  - 10K<n<100K
pretty_name: Brazilian Digital Identity on Instagram — Thematic Corpus (17,287 comments)
---

# Brazilian Digital Identity on Instagram — Thematic Corpus

**Authors:** Étore Braga e Santos (Unicamp, ORCID 0009-0000-3502-705X) & Pâmella Fernandes de Sá (USP FEA-RP)  
**License:** CC BY 4.0 (dataset) — code at https://github.com/Etore-BeS/brazilian-digital-identity-paper (MIT)  
**Version:** 1.0.0 — Collection March 7–11, 2026

## Dataset Description

Anonymized corpus of **17,287 Instagram comments** on three international celebrity posts with substantial Brazilian engagement, annotated for Brazilian digital identity (Social Identity Theory). Each comment is labeled on three axes: **theme (multi-label C1–C5 or N.A.)**, **character (Afetivo/Cognitivo)**, and **tone (Positivo/Negativo/Neutro)**. Full methodology in the GitHub repo `classification/METHODOLOGY.md`.

Cases:

| Case | Post context | N |
|------|--------------|---|
| `Bruno_Mars` | American singer Bruno Mars thanking the Brazilian audience after his tour | 8,100 |
| `Fernanda_Torres` | Official Academy Awards profile highlighting Fernanda Torres for Oscar 2025 nomination | 6,619 |
| `CR7` | Cristiano Ronaldo paying tribute to Pelé after his death | 2,568 |
| **Total** | | **17,287** |

Related TCC: *O comportamento digital dos brasileiros nas redes sociais e sua influência na construção da imagem do Brasil no exterior: uma análise netnográfica* (Sá, P. F., USP FEA-RP).

## Dataset Structure

- `data/train.csv` — one row per anonymized comment (`comment_anon`, `@handle` → `@user`, usernames removed), 26 columns. Single split (full corpus).
- `table1.csv` — aggregated Table 1 (counts and %) by case, post human review.
- `codebook.csv` — column definitions.

Key columns:

| Column | Description |
|--------|-------------|
| `hash_id` | `{CASE}_{seq}` anonymized ID |
| `case` | Bruno_Mars / Fernanda_Torres / CR7 |
| `comment_anon` | Anonymized text (input to LLM coders) |
| `emojis_list`, `hashtags_list` | Extracted emojis/hashtags |
| `language`, `is_brazilian` | langdetect (seed 42) + heuristic Brazilian flag |
| `theme_C1…C5`, `theme_NA` | Multi-label themes (C1 Nacionalismo/Orgulho, C2 Humor/Sátira/Meme, C3 Conflito/Rivalidade, C4 Validação/Afeto pelo Estrangeiro, C5 Apropriação do Espaço Digital) |
| `character`, `tone` | Single-label |
| `classification_source` | `rule` (69%), `llm_agreed`, `llm_reviewer`, `human` (188, 1.1%) |
| `human_reviewed` | True if post human adjudication (225 flagged) |

Full codebook: `codebook.csv`. Schema enforced in `classification/schema.py` (Pydantic: N.A. exclusive, max 3 C themes).

## Annotation Procedure

1. **Deterministic rules** (emoji-only, hashtags, slogans) — 11,927 rows (69.0%), first-match-wins, `classification/rules.py`.
2. **Dual LLM coders** `openai:gpt-5-nano` (Pydantic AI), identical prompts, parallel per comment with `MAX_CONCURRENT_REQUESTS=20` (`classification/agents.py`, `classification/pipeline.py`).
3. **Reviewer adjudication** `openai:gpt-5-mini` when theme sets differ (A≠B).
4. **Residual human review** when `max(κ_reviewer,A, κ_reviewer,B) < 0.80` over C1–C5 binary flags — 225 flagged, 225 reviewed, 188 recoded by domain expert (Sá, P. F.). Character/tone do not gate human review.

Inter-coder reliability (label-wise κ, A↔B, post-adjudication): C1 0.88, C2 0.79, C3 0.85, C4 0.85, C5 0.58 (C5 lowest). See `classification/METHODOLOGY.md` §9.

## Intended Uses

Research on Brazilian digital identity, netnography, multi-label thematic analysis, and LLM-assisted annotation. Not for de-anonymization or targeting individuals.

## Limitations

- 69% rule-covered without human validation; C5 reliability lowest.
- Only themes gate dual-coding/human review; character/tone single-coded when themes agree.
- `is_brazilian` is heuristic; 32% non-Brazilian retained.
- LLM non-deterministic (no temperature/seed pinned).

## How to Load

```python
import pandas as pd
df = pd.read_csv("data/train.csv")
```

## Citation

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

---

## Resumo (PT)

**Autores:** Étore Braga e Santos (Unicamp, ORCID 0009-0000-3502-705X) & Pâmella Fernandes de Sá (USP FEA-RP)  
**Licença:** CC BY 4.0 (dataset) — código em https://github.com/Etore-BeS/brazilian-digital-identity-paper (MIT)

Corpus anonimizado de **17.287 comentários do Instagram** em três posts internacionais com engajamento brasileiro, anotados em três eixos: **tema (multi-rótulo C1–C5 ou N.A.)**, **caráter (Afetivo/Cognitivo)** e **tom (Positivo/Negativo/Neutro)**.

Casos: `Bruno_Mars` (8.100), `Fernanda_Torres` (6.619), `CR7` (2.568). Metodologia completa em `classification/METHODOLOGY.md`.

Estrutura: `data/train.csv` (comentário anonimizado `comment_anon`, `@handle` → `@user`), `table1.csv` (Tabela 1 agregada), `codebook.csv` (dicionário de variáveis).

Pipeline: regras determinísticas (69%), dupla codificação LLM (`gpt-5-nano`) + adjudicação (`gpt-5-mini`) + revisão humana residual (`max κ <0.80`, 225 sinalizados, 188 recodificados pela especialista Sá, P. F.).

Coleta: 7–11 de março de 2026; `date_iso` dos comentários de dez/2022 a mar/2026. Dados anonimizados, sem interação com usuários.

Citação: ver BibTeX acima (dataset + software). TCC relacionado: *O comportamento digital dos brasileiros…* (Sá, P. F., USP FEA-RP).

## Data Availability / Disponibilidade

Collection March 7–11, 2026 (file mtimes `data/*.json`); anonymized `comment_anon` only; CC BY 4.0; version 1.0.0.
Coleta 7–11 de março de 2026; apenas `comment_anon` anonimizado; CC BY 4.0; versão 1.0.0.
