"""Core entity models from data-model.md"""

from datetime import datetime
from enum import Enum
from typing import List

from pydantic import BaseModel, Field, field_validator


class EntityType(str, Enum):
    """Entity types for canonical entities"""

    PESSOA = "Pessoa"
    GRUPO_PESSOAS = "GrupoPessoas"
    EMPRESA = "Empresa"
    NAO_DETERMINADO = "NaoDeterminado"


class ClassificationCategory(str, Enum):
    """Five classification categories from spec"""

    PESSOA = "Pessoa"
    CONJUNTO_PESSOAS = "ConjuntoPessoas"
    GRUPO_PESSOAS = "GrupoPessoas"
    EMPRESA = "Empresa"
    NAO_DETERMINADO = "NaoDeterminado"


class SeparatorType(str, Enum):
    """Separator types for atomization"""

    SEMICOLON = ";"
    AMPERSAND = "&"
    ET_AL = "et al."
    NONE = "none"


class ClassificationResult(BaseModel):
    """Result of Stage 1 classification analysis"""

    original_text: str
    category: ClassificationCategory
    confidence: float = Field(ge=0.0, le=1.0)
    patterns_matched: List[str]
    should_atomize: bool

    @field_validator("confidence")
    @classmethod
    def check_threshold(cls, v: float) -> float:
        if v < 0.70:
            raise ValueError("Confidence below threshold (0.70)")
        return v


class AtomizedName(BaseModel):
    """Individual name extracted from conjunto_pessoas"""

    text: str = Field(min_length=1)
    original_formatting: str
    position: int = Field(ge=0)
    separator_used: SeparatorType


class NormalizedName(BaseModel):
    """Standardized version of name for comparison"""

    original: str
    normalized: str
    normalization_rules_applied: List[str]

    @field_validator("normalized")
    @classmethod
    def must_be_uppercase(cls, v: str) -> str:
        if v != v.upper():
            raise ValueError("Normalized name must be uppercase")
        return v


class NameVariation(BaseModel):
    """Specific representation of a canonical entity"""

    variation_text: str
    occurrence_count: int = Field(ge=1)
    association_confidence: float = Field(ge=0.70, le=1.0)
    first_seen: datetime
    last_seen: datetime


class CanonicalEntity(BaseModel):
    """Unique collector entity with grouped variations"""

    id: int | None = None
    canonicalName: str
    entityType: EntityType
    classification_confidence: float = Field(ge=0.70, le=1.0)
    grouping_confidence: float = Field(ge=0.70, le=1.0)
    variations: List[NameVariation] = Field(min_length=1)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
