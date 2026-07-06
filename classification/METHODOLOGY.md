# Metodologia da classificação automática

Documento de referência para redigir a seção de métodos do artigo. O código vive em `classification/`; o notebook [`pipeline_extraction.ipynb`](../pipeline_extraction.ipynb) orquestra ingestão, pré-processamento e execução.

## Visão geral do pipeline

```
Comentário anonimizado + metadados
        │
        ▼
┌───────────────────┐
│ Regras (2.5)      │──► padrão determinístico ──► labels finais (sem LLM)
└─────────┬─────────┘
          │ sem regra
          ▼
┌───────────────────┐
│ Coder A ∥ Coder B │  openai:gpt-5-nano, prompts idênticos, chamadas independentes
└─────────┬─────────┘
          │
    conjunto de themes igual?
    ┌─────┴─────┐
   sim          não
    │            ▼
    │     ┌──────────────┐
    │     │ Revisor      │  openai:gpt-5-mini, vê A + B + comentário
    │     └──────┬───────┘
    │            │
    └─────┬──────┘
          ▼
   labels finais (multi-label C1–C5 ou N.A.)
          │
          │ (somente se passou pelo revisor)
          ▼
   max(κ_rev,A, κ_rev,B) < 0,80 ?
          │
         sim ──► fila de revisão humana
```

## Eixos analíticos

| Eixo | Cardinalidade | Armazenamento |
|------|---------------|---------------|
| **TEMA** | Multi-label (1–3 categorias C1–C5 simultâneas, ou N.A.) | Colunas binárias `theme_C1` … `theme_C5`, `theme_NA` |
| **CARÁTER** | Single-label | `character` (Afetivo / Cognitivo) |
| **TOM** | Single-label | `tone` (Positivo / Negativo / Neutro) |

Categorias de tema (codebook):

- **C1** — Nacionalismo/Orgulho
- **C2** — Humor/Sátira/Meme
- **C3** — Conflito/Rivalidade
- **C4** — Validação/Afeto pelo Estrangeiro
- **C5** — Apropriação do Espaço Digital
- **N.A.** — Nenhuma função identitária C1–C5 aplicável (exclusivo de C1–C5)

## Etapa 1 — Regras determinísticas (Seção 2.5)

**Objetivo:** cobrir padrões de superfície estáveis (emoji-only, slogans, hashtags de campanha) sem custo de LLM.

**Implementação:** `classification/rules.py`

**Princípios:**
- Disparam apenas em padrões conservadores e repetíveis.
- Retornam o mesmo schema que o LLM (flags multi-label + caráter + tom).
- Não passam por codificação dupla nem revisor.
- Nunca entram na fila humana.

**Exemplos de multi-label nas regras:**
- `flag_mixed_foreign` com emojis de afeto (😍💛❤️…) → `{C4, C5}`
- `national_colors_foreign` com 🇧🇷 → `{C4, C5}`

## Etapa 2 — Codificação dupla LLM (Seção 3)

**Modelo:** `openai:gpt-5-nano` (dois agentes independentes, mesmo system prompt).

**Concorrência:** A e B rodam em paralelo por comentário (`asyncio.gather`); semáforo global limita requisições simultâneas (`MAX_CONCURRENT_REQUESTS = 20`).

**Contexto enviado ao modelo:** texto anonimizado, emojis, hashtags, `POST_CONTEXT` (case), `CASE_THEME_HINT`, idioma detectado, `is_brazilian`.

**Gate pós-codificação:**
- Conjuntos de flags C1–C5 **iguais** entre A e B → aceita output de A (`classification_source = llm_agreed`).
- Conjuntos **diferentes** → aciona revisor.

## Etapa 3 — Agente revisor

**Modelo:** `openai:gpt-5-mini`

**Entrada:** comentário + contexto + codificação completa de A e B (themes, confidences, caráter, tom).

**Saída:** adjudicação final (`classification_source = llm_reviewer`).

**Papel metodológico:** reduzir ambiguidade quando os codificadores discordam, sem substituir o analista humano nos casos em que a adjudicação não converge com nenhum dos dois.

## Etapa 4 — Fila de revisão humana

**Critério (somente após revisor):**

```
needs_human_review = max(κ_rev_a, κ_rev_b) < KAPPA_HUMAN_THRESHOLD
```

com `KAPPA_HUMAN_THRESHOLD = 0.80`.

**κ por comentário:** Cohen's κ calculado sobre os 5 flags binários C1–C5 entre revisor e cada codificador.

**Racional:** quando A≠B, o revisor frequentemente alinha com um codificador (κ = 1,0) e discorda parcialmente do outro. Usar `min(κ)` mandaria quase tudo para humanos. Com `max(κ) < 0,80`, humano só quando o revisor **não** concorda substancialmente com **nenhum** dos dois — adjudicação genuinamente nova.

**Linhas com A = B** nunca vão para humano via este gate (concordância dupla suficiente).

## Confiabilidade inter-codificadores (Seção 3.5)

Dois usos de κ:

| Uso | Escopo | Função |
|-----|--------|--------|
| **Operacional** | Por comentário, subset com revisor | Gate da fila humana (`max(κ_rev,A), κ_rev,B)`) |
| **Metodológico** | Dataset LLM inteiro, label-wise | Cohen's κ global por theme entre pares de raters |

**Pares reportados no notebook:**
1. Coder A ↔ Coder B (confiabilidade inter-codificadores)
2. Revisor ↔ Coder A (subset adjudicado)
3. Revisor ↔ Coder B (subset adjudicado)

**Taxas operacionais** (`summarize_operational_rates`):
- `exact_set_agreement_rate` — % A = B (skip revisor)
- `reviewer_invocation_rate` — % com revisor
- `human_queue_rate` — % na fila humana

## Agregação (Tabela 1 — Seção 3.4)

`generate_dataset_final()` em `classification/aggregation.py`:

- **TEMA:** contagem de **presença** por flag (multi-label) — percentuais por case podem somar > 100%.
- **CARÁTER / TOM:** crosstab single-label (mutuamente exclusivo).

## Arquivos de saída

| Arquivo | Conteúdo |
|---------|----------|
| `classified_comments.csv` | Uma linha por comentário, todas as colunas de classificação e auditoria |
| `classified_comments_sample.csv` | Idem, modo amostra (`USE_SAMPLE=True`) |
| `final_dataset.csv` | Tabela agregada N e % por case |
| `final_dataset_sample.csv` | Idem, modo amostra |

## Colunas principais para o artigo

| Coluna | Descrição |
|--------|-----------|
| `theme_C1` … `theme_C5`, `theme_NA` | Labels finais (multi-label) |
| `theme_C1_a` … `theme_NA_b` | Codificações independentes A e B |
| `theme_conf`, `char_conf`, `tone_conf` | Confiança auto-reportada pelo modelo (metadado; **não** gate humano) |
| `coder_agreement` | `True` se conjuntos A = B |
| `reviewer_used` | `True` se revisor adjudicou |
| `kappa_reviewer_a`, `kappa_reviewer_b` | κ por comentário (quando revisor usado) |
| `needs_human_review` | Fila humana |
| `classification_source` | `rule` \| `llm_agreed` \| `llm_reviewer` \| `error` |
| `theme_C1_human` … `theme_C5_human` | Preenchimento manual pós-adjudicação |
| `human_reviewed` | `True` após revisão humana concluída |

## Modo amostra (teste de custo / calibração)

No notebook (`USE_SAMPLE=True`) ou via `run_classification_sample.py`:

- Amostra estratificada por `case` (`SAMPLE_SIZE`, `SAMPLE_SEED`).
- Permite validar fluxo, κ e custo antes do run completo (~17k comentários).

## Módulos

| Módulo | Responsabilidade |
|--------|------------------|
| `constants.py` | Limiares, nomes de colunas, contexto dos cases |
| `schema.py` | Schema Pydantic multi-label |
| `rules.py` | Regras determinísticas |
| `agents.py` | Prompts e factories dos agentes |
| `agreement.py` | Igualdade de conjuntos, κ, gate humano |
| `pipeline.py` | Orquestração async dual-coder + revisor |
| `aggregation.py` | Tabela 1 e cobertura de regras |
| `emoji_helpers.py` | Detecção de padrões emoji-only |

## Frases-modelo para o artigo (adaptar)

> A análise de conteúdo seguiu abordagem assistida por LLM com validação em três camadas: (1) regras determinísticas para padrões de superfície estáveis; (2) codificação dupla independente (`gpt-5-nano`) com adjudicação automática por agente revisor (`gpt-5-mini`) em caso de discordância; (3) revisão humana residual quando a adjudicação não converge substancialmente com nenhum dos codificadores (`max(κ) < 0,80` sobre flags temáticos C1–C5). Themes foram codificados em regime multi-label (até três categorias simultâneas). Reportamos Cohen's κ label-wise entre codificadores e entre revisor e codificadores.
