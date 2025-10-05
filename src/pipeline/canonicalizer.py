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

            # Add new variation (use original format from MongoDB)
            now = datetime.now()

            # Check if variation already exists (compare by original text, case-sensitive)
            existing_var = next(
                (v for v in entity.variations if v.variation_text == input_data.original_name),
                None
            )

            if existing_var:
                # Update existing variation
                existing_var.occurrence_count += 1
                existing_var.last_seen = now
            else:
                # Add new unique variation
                new_variation = CanonicalVariation(
                    variation_text=input_data.original_name,  # Store original format
                    occurrence_count=1,
                    association_confidence=sim_score,
                    first_seen=now,
                    last_seen=now
                )
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

        # Format canonical name based on entity type
        canonical_name = self._format_canonical_name(
            input_data.normalized_name,
            input_data.entityType
        )

        # Round confidence to avoid floating point precision issues
        classification_confidence = round(input_data.classification_confidence, 2)
        classification_confidence = max(0.70, classification_confidence)

        entity = CanonicalEntity(
            canonicalName=canonical_name,
            entityType=input_data.entityType,
            classification_confidence=classification_confidence,
            grouping_confidence=1.0,  # Perfect match with itself
            variations=[
                CanonicalVariation(
                    variation_text=input_data.original_name,  # Store original format from MongoDB
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

    def _format_canonical_name(self, normalized_name: str, entity_type: str) -> str:
        """
        Format canonical name according to entity type:
        - Pessoa: "Andrade, I.R." (title case)
        - Empresa/Instituição: "EMBRAPA" (uppercase)
        - GrupoPessoas: "EMBRAPA" (uppercase)
        - NaoDeterminado: original format
        """
        if entity_type == EntityType.PESSOA:
            # Title case: "ANDRADE, I.R." -> "Andrade, I.R."
            parts = normalized_name.split(',', 1)
            if len(parts) == 2:
                surname = parts[0].strip().title()
                # Handle case where second part is full name instead of initials (e.g., "Grespan, TIAGO")
                second_part = parts[1].strip()
                if '.' not in second_part and len(second_part) > 2:
                    # Full first name, convert to initial
                    initials = second_part[0].upper() + '.'
                else:
                    initials = second_part.upper()
                return f"{surname}, {initials}"
            else:
                # Check if it's "Initials Surname" format (D.R. GONZAGA) or mixed format
                name_parts = normalized_name.split()
                if len(name_parts) >= 2:
                    # Check if any part has dots (indicates initials present)
                    has_initials = any('.' in part for part in name_parts)

                    if has_initials:
                        # Mixed format: some initials, some full names
                        # Last part without dot is likely surname
                        surname_idx = -1
                        for i in range(len(name_parts) - 1, -1, -1):
                            if '.' not in name_parts[i]:
                                surname_idx = i
                                break

                        if surname_idx != -1:
                            surname = name_parts[surname_idx].title()
                            # Convert all other parts to initials
                            initial_parts = []
                            for i, part in enumerate(name_parts):
                                if i != surname_idx:
                                    if '.' in part:
                                        initial_parts.append(part.upper())
                                    else:
                                        # Full name -> initial
                                        initial_parts.append(part[0].upper() + '.')
                            initials = ''.join(initial_parts)
                            return f"{surname}, {initials}"
                    else:
                        # No initials - full names: "ALISSON NOGUEIRA BRAZ" -> "Braz, A.N."
                        surname = name_parts[-1].title()
                        initials = '.'.join([p[0].upper() for p in name_parts[:-1]]) + '.'
                        return f"{surname}, {initials}"
                else:
                    return normalized_name.title()
        elif entity_type in [EntityType.EMPRESA, EntityType.GRUPO_PESSOAS]:
            # Keep uppercase for institutions and groups
            return normalized_name.upper()
        else:
            # NãoDeterminado: keep as is
            return normalized_name
