"""Contract test for canonicalization schema"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from src.models.contracts import (
    CanonicalizationInput,
    CanonicalizationOutput,
    CanonicalEntity,
    CanonicalVariation,
    EntityType
)


class TestCanonicalizationInput:
    """Test CanonicalizationInput schema"""

    def test_valid_input(self):
        """Valid input: normalized_name, entityType, classification_confidence >= 0.70"""
        input_data = CanonicalizationInput(
            normalized_name="SILVA, J.",
            entityType=EntityType.PESSOA,
            classification_confidence=0.85
        )
        assert input_data.classification_confidence >= 0.70

    def test_confidence_below_threshold(self):
        """Invalid: classification_confidence < 0.70"""
        with pytest.raises(ValidationError):
            CanonicalizationInput(
                normalized_name="SILVA, J.",
                entityType=EntityType.PESSOA,
                classification_confidence=0.65
            )


class TestCanonicalVariation:
    """Test CanonicalVariation schema"""

    def test_valid_variation(self):
        """Valid variation with all fields"""
        variation = CanonicalVariation(
            variation_text="Silva, J.",
            occurrence_count=10,
            association_confidence=0.85,
            first_seen=datetime.now(),
            last_seen=datetime.now()
        )
        assert variation.occurrence_count >= 1
        assert variation.association_confidence >= 0.70

    def test_occurrence_count_minimum(self):
        """occurrence_count must be >= 1"""
        with pytest.raises(ValidationError):
            CanonicalVariation(
                variation_text="Test",
                occurrence_count=0,
                association_confidence=0.80,
                first_seen=datetime.now(),
                last_seen=datetime.now()
            )

    def test_association_confidence_threshold(self):
        """association_confidence must be >= 0.70"""
        with pytest.raises(ValidationError):
            CanonicalVariation(
                variation_text="Test",
                occurrence_count=1,
                association_confidence=0.65,
                first_seen=datetime.now(),
                last_seen=datetime.now()
            )


class TestCanonicalEntity:
    """Test CanonicalEntity schema"""

    def test_valid_entity(self):
        """Valid entity with all required fields"""
        entity = CanonicalEntity(
            canonicalName="Forzza, R.C.",
            entityType=EntityType.PESSOA,
            classification_confidence=0.92,
            grouping_confidence=0.88,
            variations=[
                CanonicalVariation(
                    variation_text="Forzza, R.C.",
                    occurrence_count=10,
                    association_confidence=0.95,
                    first_seen=datetime.now(),
                    last_seen=datetime.now()
                )
            ],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert entity.grouping_confidence >= 0.70
        assert len(entity.variations) >= 1

    def test_grouping_confidence_threshold(self):
        """grouping_confidence must be >= 0.70"""
        with pytest.raises(ValidationError):
            CanonicalEntity(
                canonicalName="Test",
                entityType=EntityType.PESSOA,
                classification_confidence=0.80,
                grouping_confidence=0.65,
                variations=[
                    CanonicalVariation(
                        variation_text="Test",
                        occurrence_count=1,
                        association_confidence=0.80,
                        first_seen=datetime.now(),
                        last_seen=datetime.now()
                    )
                ],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )

    def test_variations_non_empty(self):
        """variations list must have min_length=1"""
        with pytest.raises(ValidationError):
            CanonicalEntity(
                canonicalName="Test",
                entityType=EntityType.PESSOA,
                classification_confidence=0.80,
                grouping_confidence=0.80,
                variations=[],
                created_at=datetime.now(),
                updated_at=datetime.now()
            )


class TestCanonicalizationOutput:
    """Test CanonicalizationOutput schema"""

    def test_valid_output(self):
        """Valid output with entity and flags"""
        entity = CanonicalEntity(
            canonicalName="Silva, J.",
            entityType=EntityType.PESSOA,
            classification_confidence=0.85,
            grouping_confidence=0.80,
            variations=[
                CanonicalVariation(
                    variation_text="Silva, J.",
                    occurrence_count=1,
                    association_confidence=0.85,
                    first_seen=datetime.now(),
                    last_seen=datetime.now()
                )
            ],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        output = CanonicalizationOutput(
            entity=entity,
            is_new_entity=True,
            similarity_score=None
        )
        assert output.is_new_entity is True
        assert output.similarity_score is None
