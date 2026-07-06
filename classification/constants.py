"""Shared constants for comment theme classification.

Thresholds and column names referenced in the methodology (see METHODOLOGY.md).

KAPPA_HUMAN_THRESHOLD
    Per-comment gate for human review AFTER reviewer adjudication.
    Human queue when max(kappa_rev_a, kappa_rev_b) < threshold.
    Rationale: reviewer often agrees with one coder when A≠B; min() would
    send every adjudicated row to humans.

RULE_MIN_CONFIDENCE
    Minimum self-confidence assigned by deterministic rules (documentation only;
    rules never trigger human review).

MAX_CONCURRENT_REQUESTS
    Parallel HTTP cap for the async classification pipeline.
"""

KAPPA_HUMAN_THRESHOLD = 0.80
RULE_MIN_CONFIDENCE = 0.82
MAX_CONCURRENT_REQUESTS = 20

THEME_CODES = ("C1", "C2", "C3", "C4", "C5")
THEME_FLAG_COLUMNS = [f"theme_{code}" for code in THEME_CODES]
ALL_THEME_COLUMNS = [*THEME_FLAG_COLUMNS, "theme_NA"]

THEME_DISPLAY_NAMES = {
    "C1": "C1: Nacionalismo/Orgulho",
    "C2": "C2: Humor/Sátira/Meme",
    "C3": "C3: Conflito/Rivalidade",
    "C4": "C4: Validação/Afeto pelo Estrangeiro",
    "C5": "C5: Apropriação do Espaço Digital",
    "NA": "N.A.",
}

CASE_CONTEXT = {
    "Fernanda_Torres": (
        "Post by the official Academy Awards profile (@theacademy) highlighting "
        "Brazilian actress Fernanda Torres for her Oscar 2025 nomination."
    ),
    "CR7": (
        "Post by Portuguese football player Cristiano Ronaldo paying tribute to "
        "the Brazilian legend Pelé after his death."
    ),
    "Bruno_Mars": (
        "Video by American singer Bruno Mars thanking the Brazilian audience "
        "after his tour, featuring funk music and references to local culture."
    ),
}

CASE_THEME_HINT = {
    "Fernanda_Torres": (
        "Emoji-only 🇧🇷/🏆/💛/💚/❤️/👏 usually express C1 (national support). "
        "Use N.A. only for clearly off-topic spam."
    ),
    "Bruno_Mars": (
        "Emoji-only 🇧🇷/📍 usually C5; 💛/💚/❤️/😍/🔥/👏 toward Bruno usually C4. "
        "🇧🇷 combined with affect emojis may express C4 and C5 together. "
        "Do not use N.A. for short Brazilian fan reactions."
    ),
    "CR7": (
        "Emoji-only on this Pelé tribute: C1 if centered on Brazilian pride in Pelé; "
        "C4 if centered on affection toward CR7. Both may co-occur. "
        "Avoid N.A. when an identity trace exists."
    ),
}

CLASSIFICATION_COLUMNS = [
    *ALL_THEME_COLUMNS,
    "theme_conf",
    "character",
    "char_conf",
    "tone",
    "tone_conf",
    "needs_human_review",
    "coder_agreement",
    "reviewer_used",
    "kappa_reviewer_a",
    "kappa_reviewer_b",
]

AUDIT_THEME_SUFFIXES = ("a", "b")

PRICE_INPUT_TOKEN_NANO = 0.05 / 1_000_000
PRICE_OUTPUT_TOKEN_NANO = 0.4 / 1_000_000
PRICE_INPUT_TOKEN_MINI = 0.25 / 1_000_000
PRICE_OUTPUT_TOKEN_MINI = 2.0 / 1_000_000
