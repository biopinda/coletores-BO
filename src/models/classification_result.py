"""
ClassificationResult model - Entity type determination with confidence scoring

This model represents the result of classifying a collector string into one
of six entity types with confidence scoring and reasoning.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class ClassificationResult:
    """Result of collector string classification"""

    # Classification outcome
    entity_type: str                         # pessoa, conjunto_pessoas, grupo_pessoas,
                                            # empresa_instituicao, coletor_indeterminado,
                                            # representacao_insuficiente
    confidence_score: float                  # 0.0-1.0 confidence in classification
    reasoning: str                           # Human-readable explanation

    # Classification details
    detected_patterns: List[str] = field(default_factory=list)             # Regex patterns that matched
    separator_found: Optional[str] = None           # Separator used for multi-person detection
    institutional_indicators: List[str] = field(default_factory=list)      # Keywords suggesting institution

    # Metadata
    classifier_version: str = "1.0.0"                  # Version of classification algorithm
    classification_timestamp: datetime = field(default_factory=datetime.now)      # When classification occurred

    def __post_init__(self):
        """Validate classification result"""
        valid_types = [
            "pessoa", "conjunto_pessoas", "grupo_pessoas",
            "empresa_instituicao", "coletor_indeterminado", "representacao_insuficiente"
        ]

        if self.entity_type not in valid_types:
            raise ValueError(f"Invalid entity_type: {self.entity_type}. Must be one of {valid_types}")

        if not (0.0 <= self.confidence_score <= 1.0):
            raise ValueError(f"confidence_score must be between 0.0 and 1.0, got {self.confidence_score}")

    def requires_manual_review(self) -> bool:
        """Check if classification needs manual review"""
        return (self.confidence_score < 0.5 or
                self.entity_type in ["representacao_insuficiente", "coletor_indeterminado"])

    def is_canonicalizable(self) -> bool:
        """Check if result can participate in canonicalization"""
        return self.entity_type in ["pessoa", "conjunto_pessoas", "grupo_pessoas", "empresa_instituicao"]

    def is_individual_collector(self) -> bool:
        """Check if this represents a single person"""
        return self.entity_type == "pessoa"

    def is_multiple_collectors(self) -> bool:
        """Check if this represents multiple people"""
        return self.entity_type in ["conjunto_pessoas", "grupo_pessoas"]

    def is_institutional(self) -> bool:
        """Check if this represents an institution"""
        return self.entity_type == "empresa_instituicao"

    def is_problematic(self) -> bool:
        """Check if this is an indeterminate or insufficient case"""
        return self.entity_type in ["coletor_indeterminado", "representacao_insuficiente"]

    def get_quality_level(self) -> str:
        """Get quality assessment based on confidence and type"""
        if self.confidence_score >= 0.9:
            return "high"
        elif self.confidence_score >= 0.7:
            return "medium"
        elif self.confidence_score >= 0.5:
            return "low"
        else:
            return "very_low"

    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            "entity_type": self.entity_type,
            "confidence_score": self.confidence_score,
            "reasoning": self.reasoning,
            "detected_patterns": self.detected_patterns,
            "separator_found": self.separator_found,
            "institutional_indicators": self.institutional_indicators,
            "classifier_version": self.classifier_version,
            "classification_timestamp": self.classification_timestamp,
            "requires_manual_review": self.requires_manual_review(),
            "is_canonicalizable": self.is_canonicalizable(),
            "quality_level": self.get_quality_level()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'ClassificationResult':
        """Create ClassificationResult from dictionary"""
        return cls(
            entity_type=data["entity_type"],
            confidence_score=data["confidence_score"],
            reasoning=data["reasoning"],
            detected_patterns=data.get("detected_patterns", []),
            separator_found=data.get("separator_found"),
            institutional_indicators=data.get("institutional_indicators", []),
            classifier_version=data.get("classifier_version", "1.0.0"),
            classification_timestamp=data.get("classification_timestamp", datetime.now())
        )

    def __str__(self) -> str:
        """String representation for logging"""
        return f"ClassificationResult(type={self.entity_type}, confidence={self.confidence_score:.2f}, quality={self.get_quality_level()})"