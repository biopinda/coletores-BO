"""Contract test for entity schema"""

import pytest
from datetime import datetime
from pydantic import ValidationError
from src.models.contracts import CanonicalEntity, CanonicalVariation, EntityType


class TestCanonicalEntity:
    """Test CanonicalEntity schema constraints"""

    def test_all_confidence_fields_valid(self):
        """All confidence fields must be >= 0.70"""
        entity = CanonicalEntity(
            canonicalName="Test",
            entityType=EntityType.PESSOA,
            classification_confidence=0.75,
            grouping_confidence=0.80,
            variations=[
                CanonicalVariation(
                    variation_text="Test",
                    occurrence_count=1,
                    association_confidence=0.72,
                    first_seen=datetime.now(),
                    last_seen=datetime.now()
                )
            ],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert entity.classification_confidence >= 0.70
        assert entity.grouping_confidence >= 0.70
        assert all(v.association_confidence >= 0.70 for v in entity.variations)

    def test_variations_non_empty(self):
        """variations must have at least one entry"""
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

    def test_datetime_fields_populated(self):
        """Datetime fields must be populated"""
        now = datetime.now()
        entity = CanonicalEntity(
            canonicalName="Test",
            entityType=EntityType.PESSOA,
            classification_confidence=0.80,
            grouping_confidence=0.80,
            variations=[
                CanonicalVariation(
                    variation_text="Test",
                    occurrence_count=1,
                    association_confidence=0.80,
                    first_seen=now,
                    last_seen=now
                )
            ],
            created_at=now,
            updated_at=now
        )
        assert entity.created_at is not None
        assert entity.updated_at is not None


class TestNameVariation:
    """Test NameVariation schema constraints"""

    def test_occurrence_count_minimum(self):
        """occurrence_count must be >= 1"""
        variation = CanonicalVariation(
            variation_text="Test",
            occurrence_count=5,
            association_confidence=0.80,
            first_seen=datetime.now(),
            last_seen=datetime.now()
        )
        assert variation.occurrence_count >= 1

    def test_association_confidence_threshold(self):
        """association_confidence must be >= 0.70"""
        variation = CanonicalVariation(
            variation_text="Test",
            occurrence_count=1,
            association_confidence=0.95,
            first_seen=datetime.now(),
            last_seen=datetime.now()
        )
        assert variation.association_confidence >= 0.70

    def test_datetime_fields_present(self):
        """first_seen and last_seen must be present"""
        now = datetime.now()
        variation = CanonicalVariation(
            variation_text="Test",
            occurrence_count=1,
            association_confidence=0.80,
            first_seen=now,
            last_seen=now
        )
        assert variation.first_seen is not None
        assert variation.last_seen is not None
