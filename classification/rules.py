"""Deterministic rule-based classification with multi-label theme support."""

from classification.constants import RULE_MIN_CONFIDENCE
from classification.emoji_helpers import (
    AFFECT_SIGNAL_EMOJIS,
    BR_FLAG,
    BR_NATIONAL_COLORS,
    FOREIGN_CELEBRITY_CASES,
    PAT_COME_TO_BRAZIL,
    emoji_only_bucket,
    is_campaign_shell_row,
    is_emoji_only_row,
    is_flag_only_row,
)


def _rule_result(
    rule_id: str,
    themes: set[str],
    theme_confidence: float,
    character: str,
    character_confidence: float,
    tone: str,
    tone_confidence: float,
) -> dict:
    for label, value in (
        ("theme", theme_confidence),
        ("character", character_confidence),
        ("tone", tone_confidence),
    ):
        if value < RULE_MIN_CONFIDENCE:
            msg = (
                f"Rule {rule_id}: {label}_confidence={value} "
                f"< RULE_MIN_CONFIDENCE={RULE_MIN_CONFIDENCE}"
            )
            raise ValueError(msg)
    return {
        "rule_id": rule_id,
        "themes": themes,
        "theme_confidence": theme_confidence,
        "character": character,
        "character_confidence": character_confidence,
        "tone": tone,
        "tone_confidence": tone_confidence,
    }


def _emoji_affect_rule(case: str, suffix: str) -> dict:
    """Case-aware classification for generic emoji-only affect signals."""
    if case == "Fernanda_Torres":
        return _rule_result(
            f"affect_{suffix}_fernanda",
            {"C1"},
            0.86,
            "Afetivo",
            0.90,
            "Positivo",
            0.88,
        )
    if case in FOREIGN_CELEBRITY_CASES:
        return _rule_result(
            f"affect_{suffix}_foreign",
            {"C4"},
            0.84,
            "Afetivo",
            0.88,
            "Positivo",
            0.86,
        )
    return _rule_result(
        f"generic_{suffix}",
        {"NA"},
        0.92,
        "Afetivo",
        0.90,
        "Positivo",
        0.88,
    )


def _flag_mixed_themes(case: str, emoji_set: set[str]) -> set[str]:
    if case == "Fernanda_Torres":
        return {"C1"}
    if emoji_set & AFFECT_SIGNAL_EMOJIS:
        return {"C4", "C5"}
    return {"C5"}


def _national_colors_themes(case: str, emoji_set: set[str]) -> set[str]:
    if case == "Fernanda_Torres":
        return {"C1"}
    if case in FOREIGN_CELEBRITY_CASES:
        if BR_FLAG in emoji_set:
            return {"C4", "C5"}
        return {"C4"}
    return {"NA"}


def apply_rule_based_classification(row) -> dict | None:
    """Return a full classification dict for unambiguous rows; otherwise None (use LLM)."""
    emojis = row.get("emojis_list") or []
    case = row.get("case")
    norm = str(row.get("comment_norm", ""))
    emoji_set = set(emojis)

    if is_campaign_shell_row(row):
        return _rule_result(
            "rumoaos200m_shell",
            {"C5"},
            0.92,
            "Afetivo",
            0.90,
            "Positivo",
            0.88,
        )

    if PAT_COME_TO_BRAZIL.search(norm):
        return _rule_result(
            "come_to_brazil",
            {"C4"},
            0.93,
            "Afetivo",
            0.92,
            "Positivo",
            0.91,
        )

    if not is_emoji_only_row(row):
        return None

    if is_flag_only_row(row):
        if case == "Fernanda_Torres":
            return _rule_result(
                "flag_only_fernanda",
                {"C1"},
                0.86,
                "Afetivo",
                0.88,
                "Positivo",
                0.86,
            )
        return _rule_result(
            "flag_only_foreign_thread",
            {"C5"},
            0.84,
            "Afetivo",
            0.86,
            "Positivo",
            0.84,
        )

    if emojis == ["❤️"] or (len(emojis) == 1 and emojis[0] == "❤️" and norm.strip("❤️") == ""):
        return _emoji_affect_rule(case, "heart")

    if emojis == ["👏"] or (len(emojis) == 1 and emojis[0] == "👏" and norm.strip("👏") == ""):
        return _emoji_affect_rule(case, "clap")

    if emojis == ["🔥"]:
        return _emoji_affect_rule(case, "fire")

    if emoji_set and emoji_set <= BR_NATIONAL_COLORS:
        themes = _national_colors_themes(case, emoji_set)
        rule_id = (
            "national_colors_fernanda" if case == "Fernanda_Torres" else "national_colors_foreign"
        )
        return _rule_result(
            rule_id,
            themes,
            0.84 if case == "Fernanda_Torres" else 0.83,
            "Afetivo",
            0.86,
            "Positivo",
            0.84,
        )

    bucket = emoji_only_bucket(row)
    if bucket == "flag_location":
        return _rule_result(
            "flag_location",
            {"C5"},
            0.86,
            "Afetivo",
            0.88,
            "Positivo",
            0.86,
        )

    if bucket == "flag_trophy":
        if case == "Fernanda_Torres":
            return _rule_result(
                "flag_trophy_fernanda",
                {"C1"},
                0.88,
                "Afetivo",
                0.90,
                "Positivo",
                0.88,
            )
        if case in FOREIGN_CELEBRITY_CASES:
            themes = {"C1", "C4"} if case == "CR7" else {"C4"}
            return _rule_result(
                "flag_trophy_foreign",
                themes,
                0.83,
                "Afetivo",
                0.86,
                "Positivo",
                0.84,
            )

    if bucket == "flag_mixed":
        themes = _flag_mixed_themes(case, emoji_set)
        rule_id = "flag_mixed_fernanda" if case == "Fernanda_Torres" else "flag_mixed_foreign"
        return _rule_result(
            rule_id,
            themes,
            0.86 if case == "Fernanda_Torres" else 0.84,
            "Afetivo",
            0.88,
            "Positivo",
            0.86,
        )

    if bucket == "generic_affect_only":
        return _emoji_affect_rule(case, "combo")

    return None
