"""Canonicalization stage: Group similar names"""

from datetime import datetime
from src.models.contracts import (
    CanonicalizationInput,
    CanonicalizationOutput,
    CanonicalEntity,
    CanonicalVariation,
    EntityType
)
from src.algorithms.similarity import similarity_score


class Canonicalizer:
    """Canonicalizer for grouping similar names"""
    
    def __init__(self, local_db=None):
        """Initialize with optional database connection"""
        self.local_db = local_db
    
    def canonicalize(self, input_data: CanonicalizationInput) -> CanonicalizationOutput:
        """
        Find or create canonical entity, group similar variations
        """
        # If no database, create new entity
        if not self.local_db:
            return self._create_new_entity(input_data)
        
        # Find similar entities
        similar_entities = self.local_db.find_similar_entities(
            input_data.normalized_name,
            input_data.entityType,
            threshold=0.70
        )
        
        if similar_entities:
            # Update existing entity
            entity, sim_score = similar_entities[0]  # Take best match

            # Add new variation
            now = datetime.now()
            new_variation = CanonicalVariation(
                variation_text=input_data.normalized_name,
                occurrence_count=1,
                association_confidence=sim_score,
                first_seen=now,
                last_seen=now
            )
            
            # Check if variation already exists
            existing_var = next(
                (v for v in entity.variations if v.variation_text == input_data.normalized_name),
                None
            )
            
            if existing_var:
                existing_var.occurrence_count += 1
                existing_var.last_seen = now
            else:
                entity.variations.append(new_variation)
            
            entity.updated_at = now
            entity.grouping_confidence = sim_score
            
            return CanonicalizationOutput(
                entity=entity,
                is_new_entity=False,
                similarity_score=sim_score
            )
        else:
            # Create new entity
            return self._create_new_entity(input_data)
    
    def _create_new_entity(self, input_data: CanonicalizationInput) -> CanonicalizationOutput:
        """Create a new canonical entity"""
        now = datetime.now()
        
        # Format canonical name (Sobrenome, Iniciais for Pessoa)
        canonical_name = input_data.normalized_name
        
        entity = CanonicalEntity(
            canonicalName=canonical_name,
            entityType=input_data.entityType,
            classification_confidence=input_data.classification_confidence,
            grouping_confidence=1.0,  # Perfect match with itself
            variations=[
                CanonicalVariation(
                    variation_text=input_data.normalized_name,
                    occurrence_count=1,
                    association_confidence=1.0,
                    first_seen=now,
                    last_seen=now
                )
            ],
            created_at=now,
            updated_at=now
        )
        
        return CanonicalizationOutput(
            entity=entity,
            is_new_entity=True,
            similarity_score=None
        )
