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
        """Find or create canonical entity, group similar variations.

        Raises ValueError se score < 0.70.
        """
        # normalized_name já vem em uppercase (normalizer)
        normalized_name = input_data.normalized_name
        entityType = input_data.entityType
        classification_confidence = input_data.classification_confidence

        similar_entities = self.database.find_similar_entities(
            normalized_name, entityType.value, threshold=0.70
        )

        if similar_entities:
            best_entity, best_score = similar_entities[0]
            if best_score < 0.70:
                raise ValueError(
                    f"Grouping confidence {best_score:.2f} below threshold (0.70)"
                )
            now = datetime.now()
            existing_variation = next(
                (
                    v
                    for v in best_entity.variations
                    if v.variation_text.upper() == normalized_name.upper()
                ),
                None,
            )
            if existing_variation:
                existing_variation.occurrence_count += 1
                existing_variation.last_seen = now
            else:
                best_entity.variations.append(
                    NameVariation(
                        variation_text=normalized_name,  # Mantém uppercase padronizado das variações
                        occurrence_count=1,
                        association_confidence=best_score,
                        first_seen=now,
                        last_seen=now,
                    )
                )
            # Possível melhoria do canonicalName: se pessoa e nova variação tem mais tokens que o canonical atual
            if entityType == EntityType.PESSOA:
                current_tokens = best_entity.canonicalName.split()
                new_tokens = normalized_name.split()
                if len(new_tokens) > len(current_tokens):
                    best_entity.canonicalName = self._format_canonicalName(normalized_name, entityType)
            best_entity.updated_at = now
            updated_entity = self.database.upsert_entity(best_entity)
            return CanonicalizationOutput(
                entity=updated_entity, is_new_entity=False, similarity_score=best_score
            )
        else:
            canonicalName = self._format_canonicalName(normalized_name, entityType)
            now = datetime.now()
            new_entity = CanonicalEntity(
                canonicalName=canonicalName,
                entityType=entityType,
                classification_confidence=classification_confidence,
                grouping_confidence=1.0,
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
            created_entity = self.database.upsert_entity(new_entity)
            return CanonicalizationOutput(
                entity=created_entity, is_new_entity=True, similarity_score=None
            )

    def _format_canonicalName(self, normalized_name: str, entityType: EntityType) -> str:
        """Gerar canonicalName com capitalização padronizada.

        Regras para Pessoa:
        - Se formato "SOBRENOME, X. Y." (uppercase) -> converter para "Sobrenome, X. Y."
        - Caso geral: Title Case preservando pontos e vírgulas.
        Outros tipos: manter como veio (uppercase) por enquanto.
        """
        if entityType == EntityType.PESSOA:
            # Ex: "FERREIRA JUNIOR, C. A." -> "Ferreira Junior, C. A."
            parts = normalized_name.split(",")
            if len(parts) == 2:
                last_name = parts[0].title().strip()
                rest = parts[1].strip()
                # Mantém iniciais como estão (já uppercase com pontos)
                return f"{last_name}, {rest}"
            return normalized_name.title()
        return normalized_name.title()

