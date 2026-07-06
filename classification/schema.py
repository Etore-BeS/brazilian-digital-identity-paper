"""Pydantic schemas for multi-label comment classification."""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from classification.constants import THEME_CODES, THEME_FLAG_COLUMNS


class ThemeFlags(BaseModel):
    theme_C1: bool = Field(..., description="Nacionalismo/Orgulho presente")
    theme_C2: bool = Field(..., description="Humor/Sátira/Meme presente")
    theme_C3: bool = Field(..., description="Conflito/Rivalidade presente")
    theme_C4: bool = Field(..., description="Validação/Afeto pelo Estrangeiro presente")
    theme_C5: bool = Field(..., description="Apropriação do Espaço Digital presente")
    theme_NA: bool = Field(..., description="Nenhum C1–C5 aplicável")

    @model_validator(mode="after")
    def validate_theme_set(self) -> "ThemeFlags":
        c_themes = [getattr(self, col) for col in THEME_FLAG_COLUMNS]
        if self.theme_NA and any(c_themes):
            msg = "N.A. is exclusive of C1–C5"
            raise ValueError(msg)
        if not self.theme_NA and not any(c_themes):
            msg = "At least one theme or N.A. is required"
            raise ValueError(msg)
        if sum(c_themes) > 3:
            msg = "Maximum 3 simultaneous C themes"
            raise ValueError(msg)
        return self


class CommentAnalysis(ThemeFlags):
    theme_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Certainty of the assigned theme set.",
    )
    character: Literal["Afetivo", "Cognitivo"]
    character_confidence: float = Field(..., ge=0.0, le=1.0)
    tone: Literal["Positivo", "Negativo", "Neutro"]
    tone_confidence: float = Field(..., ge=0.0, le=1.0)


def theme_codes_from_flags(flags: ThemeFlags) -> frozenset[str]:
    if flags.theme_NA:
        return frozenset({"NA"})
    return frozenset(code for code in THEME_CODES if getattr(flags, f"theme_{code}"))


def theme_flags_vector(flags: ThemeFlags) -> list[bool]:
    return [getattr(flags, col) for col in THEME_FLAG_COLUMNS]


def flags_to_columns(flags: ThemeFlags, *, suffix: str = "") -> dict[str, bool]:
    affix = f"_{suffix}" if suffix else ""
    return {f"{col}{affix}": getattr(flags, col) for col in [*THEME_FLAG_COLUMNS, "theme_NA"]}


def themes_set_to_flags(themes: set[str]) -> dict[str, bool]:
    if "NA" in themes:
        return {col: False for col in THEME_FLAG_COLUMNS} | {"theme_NA": True}
    return {f"theme_{code}": code in themes for code in THEME_CODES} | {"theme_NA": False}


def analysis_from_rule_dict(rule: dict) -> CommentAnalysis:
    return CommentAnalysis(
        **themes_set_to_flags(rule["themes"]),
        theme_confidence=rule["theme_confidence"],
        character=rule["character"],
        character_confidence=rule["character_confidence"],
        tone=rule["tone"],
        tone_confidence=rule["tone_confidence"],
    )
