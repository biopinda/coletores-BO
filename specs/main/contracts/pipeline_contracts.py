"""
Pipeline Stage Contracts - Type definitions and interfaces for each processing stage.

This file defines the contracts (interfaces/protocols) that each pipeline stage must implement.
These contracts serve as the foundation for contract tests.
"""

from typing import Protocol, List
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime


# ============================================================================
# Enums
# ============================================================================

class ClassificationCategory(str, Enum):
    """Five classification categories from spec"""
    PESSOA = "Pessoa"
    CONJUNTO_PESSOAS = "ConjuntoPessoas"
    GRUPO_PESSOAS = "GrupoPessoas"
    EMPRESA = "Empresa"
    NAO_DETERMINADO = "NaoDeterminado"


class EntityType(str, Enum):
    """Entity types for canonical entities"""
    PESSOA = "Pessoa"
    GRUPO_PESSOAS = "GrupoPessoas"
    EMPRESA = "Empresa"
    NAO_DETERMINADO = "NaoDeterminado"


class SeparatorType(str, Enum):
    """Separator types for atomization"""
    SEMICOLON = ";"
    AMPERSAND = "&"
    ET_AL = "et al."
    NONE = "none"


# ============================================================================
# Stage Input/Output Models
# ============================================================================

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

    class Config:
        json_schema_extra = {
            "example": {
                "original_text": "Silva, J. & R.C. Forzza",
                "category": "ConjuntoPessoas",
                "confidence": 0.95,
                "patterns_matched": ["multiple_names", "ampersand_separator"],
                "should_atomize": True
            }
        }


class AtomizationInput(BaseModel):
    """Input contract for atomization stage"""
    text: str = Field(min_length=1)
    category: ClassificationCategory


class AtomizedName(BaseModel):
    """Individual atomized name (FR-008, FR-009, FR-010)"""
    text: str = Field(min_length=1, description="Individual name extracted")
    original_formatting: str = Field(description="Preserved original format")
    position: int = Field(ge=0, description="Position in original string")
    separator_used: SeparatorType


class AtomizationOutput(BaseModel):
    """Output contract for atomization stage"""
    original_text: str
    atomized_names: List[AtomizedName] = Field(description="Empty if not ConjuntoPessoas")

    class Config:
        json_schema_extra = {
            "example": {
                "original_text": "Silva, J. & R.C. Forzza; Santos, M.",
                "atomized_names": [
                    {"text": "Silva, J.", "original_formatting": "Silva, J.", "position": 0, "separator_used": "&"},
                    {"text": "R.C. Forzza", "original_formatting": "R.C. Forzza", "position": 1, "separator_used": ";"},
                    {"text": "Santos, M.", "original_formatting": "Santos, M.", "position": 2, "separator_used": "none"}
                ]
            }
        }


class NormalizationInput(BaseModel):
    """Input contract for normalization stage"""
    original_name: str = Field(min_length=1)


class NormalizationOutput(BaseModel):
    """Output contract for normalization stage (FR-011, FR-012)"""
    original: str
    normalized: str = Field(description="Uppercase, standardized punctuation, trimmed spaces")
    rules_applied: List[str] = Field(description="Normalization rules applied")

    class Config:
        json_schema_extra = {
            "example": {
                "original": "  Silva,J.C. ",
                "normalized": "SILVA, J.C.",
                "rules_applied": ["remove_extra_spaces", "standardize_punctuation", "uppercase"]
            }
        }


class CanonicalVariation(BaseModel):
    """Name variation within canonical entity"""
    variation_text: str
    occurrence_count: int = Field(ge=1)
    association_confidence: float = Field(ge=0.70, le=1.0)
    first_seen: datetime
    last_seen: datetime


class CanonicalEntity(BaseModel):
    """Canonical entity with variations (FR-013, FR-014, FR-015, FR-016)"""
    id: int | None = None
    canonicalName: str = Field(description="Standardized 'Sobrenome, Iniciais' format for Pessoa")
    entityType: EntityType
    classification_confidence: float = Field(ge=0.70, le=1.0)
    grouping_confidence: float = Field(ge=0.70, le=1.0, description="Confidence of variation grouping")
    variations: List[CanonicalVariation] = Field(min_length=1)
    created_at: datetime
    updated_at: datetime

    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "canonicalName": "Forzza, R.C.",
                "entityType": "Pessoa",
                "classification_confidence": 0.92,
                "grouping_confidence": 0.88,
                "variations": [
                    {
                        "variation_text": "Forzza, R.C.",
                        "occurrence_count": 1523,
                        "association_confidence": 0.95,
                        "first_seen": "2025-10-03T10:00:00Z",
                        "last_seen": "2025-10-03T15:00:00Z"
                    }
                ],
                "created_at": "2025-10-03T10:00:00Z",
                "updated_at": "2025-10-03T15:00:00Z"
            }
        }


class CanonicalizationInput(BaseModel):
    """Input contract for canonicalization stage"""
    normalized_name: str
    entityType: EntityType
    classification_confidence: float = Field(ge=0.70, le=1.0)


class CanonicalizationOutput(BaseModel):
    """Output contract for canonicalization stage"""
    entity: CanonicalEntity
    is_new_entity: bool = Field(description="True if new entity created, False if existing updated")
    similarity_score: float | None = Field(ge=0.0, le=1.0, description="Score with matched entity (None if new)")


class CSVReportRow(BaseModel):
    """CSV export row format (FR-025)"""
    canonicalName: str
    variations: str = Field(description="Semicolon-separated variation texts")
    occurrenceCounts: str = Field(description="Semicolon-separated counts aligned with variations")

    class Config:
        json_schema_extra = {
            "example": {
                "canonicalName": "Forzza, R.C.",
                "variations": "Forzza, R.C.;R.C. Forzza;Rafaela C. Forzza",
                "occurrenceCounts": "1523;847;234"
            }
        }


# ============================================================================
# Pipeline Stage Protocols (Interfaces)
# ============================================================================

class ClassifierProtocol(Protocol):
    """Contract for classification stage implementation (FR-001 to FR-007)"""

    def classify(self, input: ClassificationInput) -> ClassificationOutput:
        """
        Classify input string into one of 5 categories with confidence score.

        Args:
            input: ClassificationInput containing raw text

        Returns:
            ClassificationOutput with category, confidence, and atomization flag

        Raises:
            ValueError: If confidence < 0.70 (below threshold from spec)
        """
        ...


class AtomizerProtocol(Protocol):
    """Contract for atomization stage implementation (FR-008 to FR-010)"""

    def atomize(self, input: AtomizationInput) -> AtomizationOutput:
        """
        Separate ConjuntoPessoas strings into individual names.

        Args:
            input: AtomizationInput with text and category

        Returns:
            AtomizationOutput with list of atomized names (empty if not ConjuntoPessoas)
        """
        ...


class NormalizerProtocol(Protocol):
    """Contract for normalization stage implementation (FR-011, FR-012)"""

    def normalize(self, input: NormalizationInput) -> NormalizationOutput:
        """
        Normalize name: remove extra spaces, standardize punctuation, uppercase.

        Args:
            input: NormalizationInput with original name

        Returns:
            NormalizationOutput with normalized name and rules applied
        """
        ...


class CanonicalizerProtocol(Protocol):
    """Contract for canonicalization stage implementation (FR-013 to FR-016)"""

    def canonicalize(self, input: CanonicalizationInput) -> CanonicalizationOutput:
        """
        Find or create canonical entity, group similar variations.

        Args:
            input: CanonicalizationInput with normalized name and metadata

        Returns:
            CanonicalizationOutput with entity and creation/update flag

        Raises:
            ValueError: If grouping confidence < 0.70 (below threshold)
        """
        ...


# ============================================================================
# Storage Contracts
# ============================================================================

class LocalDatabaseProtocol(Protocol):
    """Contract for local database implementation (FR-022, FR-023, FR-024)"""

    def upsert_entity(self, entity: CanonicalEntity) -> CanonicalEntity:
        """Insert new or update existing canonical entity"""
        ...

    def find_similar_entities(
        self,
        normalized_name: str,
    entityType: EntityType,
        threshold: float = 0.70
    ) -> List[tuple[CanonicalEntity, float]]:
        """Find entities with similarity >= threshold, return with scores"""
        ...

    def get_all_entities(self) -> List[CanonicalEntity]:
        """Retrieve all canonical entities for CSV export"""
        ...

    def export_to_csv(self, output_path: str) -> None:
    """Export entities to CSV format (4 columns: canonicalName, entityType, variations, occurrenceCounts)"""
        ...


class MongoDBSourceProtocol(Protocol):
    """Contract for MongoDB source reader (FR-017, FR-018)"""

    def stream_records(self, batch_size: int = 1000):
        """Stream records where kingdom=='Plantae', yield in batches"""
        ...

    def get_total_count(self) -> int:
        """Get total count of Plantae records for progress tracking"""
        ...


# ============================================================================
# Performance Contracts
# ============================================================================

class PerformanceMetrics(BaseModel):
    """Performance tracking (FR-020, FR-021)"""
    total_records: int
    processed_records: int
    records_per_second: float
    elapsed_time_seconds: float
    estimated_time_remaining_seconds: float | None

    @property
    def is_on_track(self) -> bool:
        """Check if processing rate meets 6-hour target (213 rec/sec)"""
        return self.records_per_second >= 213.0
