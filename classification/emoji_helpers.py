"""Emoji-only row detection helpers shared by rules and profiling."""

import re

import emoji

BR_FLAG = "🇧🇷"

GENERIC_AFFECT_EMOJIS = frozenset(
    {
        "❤️",
        "😍",
        "👏",
        "🔥",
        "😂",
        "🙌",
        "💯",
        "✨",
        "💙",
        "💚",
        "💛",
        "🥰",
        "😘",
        "🤣",
        "💀",
        "👍",
        "🎉",
        "😭",
        "🙏",
        "💖",
        "😢",
        "🏆",
    }
)

AFFECT_SIGNAL_EMOJIS = frozenset({"😍", "💛", "💚", "❤️", "🔥", "👏", "🥰", "😘"})

BR_NATIONAL_COLORS = frozenset({"💛", "💚"})
FOREIGN_CELEBRITY_CASES = frozenset({"Bruno_Mars", "CR7"})

PAT_COME_TO_BRAZIL = re.compile(
    r"come\s+to+\s+bra[sz]il|vem\s+(pro|para\s+o)\s+brasil|brasii+i+l",
    re.IGNORECASE,
)
PAT_RUMO_200M = re.compile(r"rumoaos200m", re.IGNORECASE)


def strip_non_emoji_text(text: str) -> str:
    """Remove @handles, hashtags, and emoji graphemes; keep remaining literal text."""
    t = re.sub(r"@(?:user|[\w.]+)", "", str(text))
    t = re.sub(r"#[\w\u00c0-\u024f]+", "", t, flags=re.UNICODE)
    return emoji.replace_emoji(t, replace="").strip()


def is_emoji_only_row(row) -> bool:
    return strip_non_emoji_text(row.get("comment_anon", "")) == "" and bool(row.get("emojis_list"))


def is_flag_only_row(row) -> bool:
    emojis = row.get("emojis_list") or []
    return (
        bool(emojis)
        and set(emojis) == {BR_FLAG}
        and strip_non_emoji_text(row.get("comment_anon", "")) == ""
    )


def emoji_only_bucket(row) -> str | None:
    if not is_emoji_only_row(row):
        return None

    emojis = row.get("emojis_list") or []
    emoji_set = set(emojis)

    if emoji_set == {BR_FLAG}:
        return "flag_only"
    if BR_FLAG in emoji_set and "📍" in emoji_set:
        return "flag_location"
    if BR_FLAG in emoji_set and "🏆" in emoji_set:
        return "flag_trophy"
    if BR_FLAG in emoji_set:
        return "flag_mixed"
    if emoji_set.issubset(GENERIC_AFFECT_EMOJIS):
        return "generic_affect_only"
    return "other_emoji_only"


def is_campaign_shell_row(row) -> bool:
    text = str(row.get("comment_anon", ""))
    norm = str(row.get("comment_norm", ""))
    return bool(PAT_RUMO_200M.search(norm)) and strip_non_emoji_text(text) == ""
