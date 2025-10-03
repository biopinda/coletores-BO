"""Input/output schemas matching pipeline_contracts.py"""

from typing import List

from pydantic import BaseModel, Field

from src.models.entities import (
    AtomizedName,
    CanonicalEntity,
    ClassificationCategory,
    EntityType,
)


class ClassificationInput(BaseModel):
    """Input contract for classification stage"""

    text: str = Field(min_length=1, description="Raw collector string from MongoDB")


class ClassificationOutput(BaseModel):
    """Output contract for classification stage (FR-001, FR-002)"""

    original_text: str
    category: ClassificationCategory
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score 0.0-1.0")
    patterns_matched: List[str] = Field(description="Patterns that triggered classification")
    should_atomize: bool = Field(description="True if category is ConjuntoPessoas")


class AtomizationInput(BaseModel):
    """Input contract for atomization stage"""

    text: str = Field(min_length=1)
    category: ClassificationCategory


class AtomizationOutput(BaseModel):
    """Output contract for atomization stage"""

    original_text: str
    atomized_names: List[AtomizedName] = Field(description="Empty if not ConjuntoPessoas")


class NormalizationInput(BaseModel):
    """Input contract for normalization stage"""

    original_name: str = Field(min_length=1)


class NormalizationOutput(BaseModel):
    """Output contract for normalization stage (FR-011, FR-012)"""

    original: str
    normalized: str = Field(description="Uppercase, standardized punctuation, trimmed spaces")
    rules_applied: List[str] = Field(description="Normalization rules applied")


class CanonicalizationInput(BaseModel):
    """Input contract for canonicalization stage"""

    normalized_name: str
    entityType: EntityType
    classification_confidence: float = Field(ge=0.70, le=1.0)


class CanonicalizationOutput(BaseModel):
    """Output contract for canonicalization stage"""

    entity: CanonicalEntity
    is_new_entity: bool = Field(
        description="True if new entity created, False if existing updated"
    )
    similarity_score: float | None = Field(
        ge=0.0, le=1.0, description="Score with matched entity (None if new)"
    )


class CSVReportRow(BaseModel):
    """CSV export row format (FR-025)"""

    canonicalName: str
    variations: str = Field(description="Semicolon-separated variation texts")
    occurrenceCounts: str = Field(description="Semicolon-separated counts aligned with variations")
