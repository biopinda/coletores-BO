"""Canonicalization stage: Group similar names under canonical entities"""

from datetime import datetime

from src.algorithms.similarity import similarity_score
from src.models.entities import CanonicalEntity, EntityType, NameVariation
from src.models.schemas import CanonicalizationInput, CanonicalizationOutput
from src.storage.local_db import LocalDatabase


class Canonicalizer:
    """Canonicalizer for name grouping (FR-013 to FR-016)"""

    def __init__(self, database: LocalDatabase):
        """Initialize with database connection"""
        self.database = database

    def canonicalize(self, input_data: CanonicalizationInput) -> CanonicalizationOutput:
        """
        Find or create canonical entity, group similar variations.

        Args:
            input_data: CanonicalizationInput with normalized name and metadata

        Returns:
            CanonicalizationOutput with entity and creation/update flag

        Raises:
            ValueError: If grouping confidence < 0.70 (below threshold)
        """
        normalized_name = input_data.normalized_name
        entity_type = input_data.entity_type
        classification_confidence = input_data.classification_confidence

        # Find similar entities
        similar_entities = self.database.find_similar_entities(
            normalized_name, entity_type.value, threshold=0.70
        )

        if similar_entities:
            # Use the most similar entity
            best_entity, best_score = similar_entities[0]

            # Check if grouping confidence meets threshold
            if best_score < 0.70:
                raise ValueError(
                    f"Grouping confidence {best_score:.2f} below threshold (0.70)"
                )

            # Update existing entity with new variation
            now = datetime.now()

            # Check if this variation already exists
            existing_variation = None
            for var in best_entity.variations:
                if var.variation_text == normalized_name:
                    existing_variation = var
                    break

            if existing_variation:
                # Update existing variation
                existing_variation.occurrence_count += 1
                existing_variation.last_seen = now
            else:
                # Add new variation
                new_variation = NameVariation(
                    variation_text=normalized_name,
                    occurrence_count=1,
                    association_confidence=best_score,
                    first_seen=now,
                    last_seen=now,
                )
                best_entity.variations.append(new_variation)

            # Update entity timestamp
            best_entity.updated_at = now

            # Upsert to database
            updated_entity = self.database.upsert_entity(best_entity)

            return CanonicalizationOutput(
                entity=updated_entity, is_new_entity=False, similarity_score=best_score
            )

        else:
            # Create new canonical entity
            canonical_name = self._format_canonical_name(normalized_name, entity_type)
            now = datetime.now()

            new_entity = CanonicalEntity(
                canonical_name=canonical_name,
                entity_type=entity_type,
                classification_confidence=classification_confidence,
                grouping_confidence=1.0,  # New entity, perfect match with itself
                variations=[
                    NameVariation(
                        variation_text=normalized_name,
                        occurrence_count=1,
                        association_confidence=1.0,
                        first_seen=now,
                        last_seen=now,
                    )
                ],
                created_at=now,
                updated_at=now,
            )

            # Insert to database
            created_entity = self.database.upsert_entity(new_entity)

            return CanonicalizationOutput(
                entity=created_entity, is_new_entity=True, similarity_score=None
            )

    def _format_canonical_name(self, normalized_name: str, entity_type: EntityType) -> str:
        """
        Format canonical name according to entity type.

        For Pessoa: "Sobrenome, Iniciais" format with proper capitalization
        For others: Use normalized name as-is

        Args:
            normalized_name: Normalized name string
            entity_type: Entity type

        Returns:
            Formatted canonical name
        """
        if entity_type == EntityType.PESSOA:
            # Try to extract "Sobrenome, Iniciais" format
            # If already in that format, use as-is
            if "," in normalized_name:
                # Apply proper capitalization (Title Case)
                return normalized_name.title()
            else:
                # Best effort: use as-is with proper capitalization
                return normalized_name.title()
        else:
            # For non-Pessoa types, use normalized name as canonical
            return normalized_name
