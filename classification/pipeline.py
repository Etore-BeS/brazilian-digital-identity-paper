"""Async dual-coder classification pipeline with reviewer and kappa gate.

Flow per comment (see classification/METHODOLOGY.md):

1. Rule hit → final labels, source=rule
2. Else: Coder A and B in parallel (gpt-5-nano)
3. Theme sets equal → accept A, source=llm_agreed
4. Theme sets differ → Reviewer (gpt-5-mini) adjudicates
5. If reviewer used: human queue when max(kappa_rev, coder) < KAPPA_HUMAN_THRESHOLD

Entry point: classify_all_comments(df)
"""

import asyncio
from typing import Any

from classification.agents import create_coder_agent, create_reviewer_agent
from classification.agreement import (
    needs_human_review_after_reviewer,
    theme_sets_equal,
)
from classification.constants import (
    CASE_CONTEXT,
    CASE_THEME_HINT,
    MAX_CONCURRENT_REQUESTS,
)
from classification.rules import apply_rule_based_classification
from classification.schema import (
    CommentAnalysis,
    analysis_from_rule_dict,
    flags_to_columns,
    theme_codes_from_flags,
    themes_set_to_flags,
)


def build_user_content(row_data) -> str:
    text = row_data.get("comment_anon", "")
    emojis = row_data.get("emojis_list", [])
    case = row_data.get("case", "unknown")
    language = row_data.get("language", "unknown")
    is_brazilian = row_data.get("is_brazilian", False)
    hashtags = row_data.get("hashtags_list", [])

    case_context = CASE_CONTEXT.get(case, f"Unknown post context for case '{case}'.")
    case_theme_hint = CASE_THEME_HINT.get(case, "")

    context_block = f"POST_CONTEXT: {case_context}\nCASE: {case}\n"
    if case_theme_hint:
        context_block += f"CASE_THEME_HINT: {case_theme_hint}\n"
    context_block += f"DETECTED_LANGUAGE: {language}\nLIKELY_BRAZILIAN_USER: {is_brazilian}\n"

    if len(str(text).replace("@user", "").strip()) < 2 and emojis:
        return (
            f"{context_block}"
            f"COMMENT_SHAPE: EMOJI-ONLY or mention-only.\n"
            f"EMOJIS: {emojis}\n"
            f"HASHTAGS: {hashtags}"
        )
    return f"{context_block}TEXT: {text}\nEMOJIS: {emojis}\nHASHTAGS: {hashtags}"


def build_reviewer_content(
    user_content: str,
    coder_a: CommentAnalysis,
    coder_b: CommentAnalysis,
) -> str:
    def fmt_flags(analysis: CommentAnalysis, label: str) -> str:
        flags = themes_set_to_flags(set(theme_codes_from_flags(analysis)))
        active = [key.replace("theme_", "") for key, val in flags.items() if val]
        return (
            f"{label} themes: {', '.join(active)}\n"
            f"{label} theme_confidence: {analysis.theme_confidence}\n"
            f"{label} character: {analysis.character} ({analysis.character_confidence})\n"
            f"{label} tone: {analysis.tone} ({analysis.tone_confidence})"
        )

    return (
        f"{user_content}\n\n"
        f"--- DISAGREEMENT: adjudicate final labels ---\n"
        f"{fmt_flags(coder_a, 'Coder A')}\n"
        f"{fmt_flags(coder_b, 'Coder B')}"
    )


def analysis_to_result_row(
    final: CommentAnalysis,
    *,
    coder_a: CommentAnalysis | None = None,
    coder_b: CommentAnalysis | None = None,
    coder_agreement: bool,
    reviewer_used: bool,
    needs_human_review: bool,
    classification_source: str,
    kappa_reviewer_a: float | None = None,
    kappa_reviewer_b: float | None = None,
    rule_id: str | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        **flags_to_columns(final),
        "theme_conf": final.theme_confidence,
        "character": final.character,
        "char_conf": final.character_confidence,
        "tone": final.tone,
        "tone_conf": final.tone_confidence,
        "needs_human_review": needs_human_review,
        "coder_agreement": coder_agreement,
        "reviewer_used": reviewer_used,
        "kappa_reviewer_a": kappa_reviewer_a,
        "kappa_reviewer_b": kappa_reviewer_b,
    }
    if coder_a is not None:
        row.update(flags_to_columns(coder_a, suffix="a"))
    if coder_b is not None:
        row.update(flags_to_columns(coder_b, suffix="b"))
    return row


def rule_to_result_row(rule: dict) -> dict[str, Any]:
    analysis = analysis_from_rule_dict(rule)
    row = analysis_to_result_row(
        analysis,
        coder_agreement=True,
        reviewer_used=False,
        needs_human_review=False,
        classification_source="rule",
    )
    row["rule_id"] = rule["rule_id"]
    return row


def error_result_row() -> dict[str, Any]:
    analysis = CommentAnalysis(
        theme_C1=False,
        theme_C2=False,
        theme_C3=False,
        theme_C4=False,
        theme_C5=False,
        theme_NA=True,
        theme_confidence=0.0,
        character="Afetivo",
        character_confidence=0.0,
        tone="Neutro",
        tone_confidence=0.0,
    )
    row = analysis_to_result_row(
        analysis,
        coder_agreement=False,
        reviewer_used=False,
        needs_human_review=True,
        classification_source="error",
    )
    return row


async def classify_all_comments(
    df,
    *,
    semaphore_limit: int = MAX_CONCURRENT_REQUESTS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    coder_agent = create_coder_agent()
    reviewer_agent = create_reviewer_agent()
    semaphore = asyncio.Semaphore(semaphore_limit)
    total = len(df)

    async def process_single(row_data):
        rule = apply_rule_based_classification(row_data)
        if rule is not None:
            meta = {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "source": "rule",
                "rule_id": rule["rule_id"],
            }
            return rule_to_result_row(rule), meta

        user_content = build_user_content(row_data)
        row_idx = row_data.name

        async with semaphore:
            try:
                result_a, result_b = await asyncio.gather(
                    coder_agent.run(user_content),
                    coder_agent.run(user_content),
                )
                coder_a = result_a.output
                coder_b = result_b.output
                input_tokens = result_a.usage().input_tokens + result_b.usage().input_tokens
                output_tokens = result_a.usage().output_tokens + result_b.usage().output_tokens

                agreed = theme_sets_equal(coder_a, coder_b)
                if agreed:
                    row = analysis_to_result_row(
                        coder_a,
                        coder_a=coder_a,
                        coder_b=coder_b,
                        coder_agreement=True,
                        reviewer_used=False,
                        needs_human_review=False,
                        classification_source="llm_agreed",
                    )
                    meta = {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens,
                        "nano_input_tokens": input_tokens,
                        "nano_output_tokens": output_tokens,
                        "mini_input_tokens": 0,
                        "mini_output_tokens": 0,
                        "source": "llm_agreed",
                        "rule_id": None,
                    }
                    return row, meta

                reviewer_content = build_reviewer_content(user_content, coder_a, coder_b)
                review_result = await reviewer_agent.run(reviewer_content)
                reviewer = review_result.output
                mini_input = review_result.usage().input_tokens
                mini_output = review_result.usage().output_tokens
                input_tokens += mini_input
                output_tokens += mini_output

                needs_review, kappa_a, kappa_b = needs_human_review_after_reviewer(
                    reviewer, coder_a, coder_b
                )
                row = analysis_to_result_row(
                    reviewer,
                    coder_a=coder_a,
                    coder_b=coder_b,
                    coder_agreement=False,
                    reviewer_used=True,
                    needs_human_review=needs_review,
                    classification_source="llm_reviewer",
                    kappa_reviewer_a=kappa_a,
                    kappa_reviewer_b=kappa_b,
                )
                meta = {
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "total_tokens": input_tokens + output_tokens,
                    "nano_input_tokens": input_tokens - mini_input,
                    "nano_output_tokens": output_tokens - mini_output,
                    "mini_input_tokens": mini_input,
                    "mini_output_tokens": mini_output,
                    "source": "llm_reviewer",
                    "rule_id": None,
                }
                return row, meta
            except Exception as exc:
                print(f"Erro na linha {row_idx}: {exc}")
                return error_result_row(), {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "total_tokens": 0,
                    "source": "error",
                    "rule_id": None,
                }

    tasks = [process_single(row) for _, row in df.iterrows()]
    n_rules = sum(apply_rule_based_classification(row) is not None for _, row in df.iterrows())
    print(
        f"Iniciando classificação PARALELA de {total} comentários "
        f"({n_rules:,} via regras, {total - n_rules:,} via LLM dual-coder)..."
    )

    from tqdm.asyncio import tqdm

    all_results = await tqdm.gather(*tasks)
    results_list = [r[0] for r in all_results]
    metadata_list = [r[1] for r in all_results]
    return results_list, metadata_list
