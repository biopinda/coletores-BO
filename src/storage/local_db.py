"""Local database implementation using DuckDB"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import duckdb
import pandas as pd

from src.algorithms.similarity import similarity_score
from src.models.entities import CanonicalEntity, NameVariation


class LocalDatabase:
    """DuckDB-based local database for canonical entities"""

    def __init__(self, db_path: str):
        """Initialize database connection and create schema"""
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(db_path)
        self._create_schema()

    @staticmethod
    def _fix_confidence(confidence: float) -> float:
        """Ensure confidence is at least 0.70 (handle floating point precision)"""
        if confidence < 0.70:
            return 0.70
        elif confidence < 0.701:  # Handle 0.6999999...
            return 0.70
        return round(confidence, 2)

    def _create_schema(self) -> None:
        """Create canonical_entities table with schema from data-model.md"""
        # Create sequence for ID
        self.conn.execute("CREATE SEQUENCE IF NOT EXISTS canonical_entities_id_seq")

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS canonical_entities (
                id INTEGER PRIMARY KEY DEFAULT nextval('canonical_entities_id_seq'),
                canonicalName TEXT NOT NULL,
                entityType TEXT NOT NULL CHECK(entityType IN ('Pessoa', 'GrupoPessoas', 'Empresa', 'NaoDeterminado')),
                classification_confidence REAL NOT NULL CHECK(classification_confidence >= 0.70 AND classification_confidence <= 1.0),
                grouping_confidence REAL NOT NULL CHECK(grouping_confidence >= 0.70 AND grouping_confidence <= 1.0),
                variations JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Non-unique index for better performance (allow temporary duplicates)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_canonicalName_type ON canonical_entities(canonicalName, entityType)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_entityType ON canonical_entities(entityType)"
        )

    def upsert_entity(self, entity: CanonicalEntity) -> CanonicalEntity:
        """Insert new or update existing canonical entity"""
        # Serialize variations to JSON with UTF-8 encoding
        variations_json = json.dumps(
            [
                {
                    "variation_text": v.variation_text,
                    "occurrence_count": v.occurrence_count,
                    "association_confidence": v.association_confidence,
                    "first_seen": v.first_seen.isoformat(),
                    "last_seen": v.last_seen.isoformat(),
                }
                for v in entity.variations
            ],
            ensure_ascii=False  # Preserve UTF-8 characters
        )

        if entity.id is None:
            # Verificar existência prévia (case-insensitive)
            existing = self.get_entity_by_canonical_upper(entity.canonicalName.upper(), entity.entityType.value)
            if existing:
                # Mesclar variações
                existing_map = {v.variation_text: v for v in existing.variations}
                for v in entity.variations:
                    if v.variation_text in existing_map:
                        existing_map[v.variation_text].occurrence_count += v.occurrence_count
                        existing_map[v.variation_text].last_seen = max(
                            existing_map[v.variation_text].last_seen, v.last_seen
                        )
                    else:
                        existing.variations.append(v)
                existing.updated_at = datetime.now()
                # Substituir objeto alvo pelo existente mesclado
                entity = existing
                entity.id = existing.id
                # Re-serializar variações após merge
                variations_json = json.dumps(
                    [
                        {
                            "variation_text": v.variation_text,
                            "occurrence_count": v.occurrence_count,
                            "association_confidence": v.association_confidence,
                            "first_seen": v.first_seen.isoformat(),
                            "last_seen": v.last_seen.isoformat(),
                        }
                        for v in entity.variations
                    ],
                    ensure_ascii=False,
                )
                # Cai no bloco de update abaixo
            else:
                # Insert new entity
                result = self.conn.execute(
                """
                INSERT INTO canonical_entities
                (canonicalName, entityType, classification_confidence, grouping_confidence,
                 variations, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                [
                    entity.canonicalName,
                    entity.entityType.value,
                    self._fix_confidence(entity.classification_confidence),
                    entity.grouping_confidence,
                    variations_json,
                    entity.created_at,
                    entity.updated_at,
                ],
            ).fetchone()
            entity.id = result[0]
        if entity.id is not None:
            # Update existing entity
            self.conn.execute(
                """
                UPDATE canonical_entities
                SET canonicalName = ?, entityType = ?, classification_confidence = ?,
                    grouping_confidence = ?, variations = ?, updated_at = ?
                WHERE id = ?
                """,
                [
                    entity.canonicalName,
                    entity.entityType.value,
                    self._fix_confidence(entity.classification_confidence),
                    entity.grouping_confidence,
                    variations_json,
                    entity.updated_at,
                    entity.id,
                ],
            )

        return entity

    def consolidate_duplicates(self) -> int:
        """Consolidar duplicatas (mesmo canonicalName/entityType) mesclando variações.

        Retorna número de grupos consolidados.
        """
        dups = self.conn.execute(
            """
            SELECT canonicalName, entityType, COUNT(*) c
            FROM canonical_entities
            GROUP BY 1,2 HAVING c > 1
            """
        ).fetchall()
        consolidated = 0
        for canonicalName, entityType, _ in dups:
            rows = self.conn.execute(
                "SELECT * FROM canonical_entities WHERE canonicalName = ? AND entityType = ? ORDER BY id",
                [canonicalName, entityType],
            ).fetchall()
            if len(rows) < 2:
                continue
            # Keep first
            primary_row = rows[0]
            keeper = self._row_to_entity(primary_row)
            variation_map = {v.variation_text: v for v in keeper.variations}
            # Merge others
            for row in rows[1:]:
                ent = self._row_to_entity(row)
                for v in ent.variations:
                    if v.variation_text in variation_map:
                        existing = variation_map[v.variation_text]
                        existing.occurrence_count += v.occurrence_count
                        existing.last_seen = max(existing.last_seen, v.last_seen)
                    else:
                        variation_map[v.variation_text] = v
            # Rebuild keeper variations list
            keeper.variations = list(variation_map.values())
            keeper.updated_at = datetime.now()
            self.upsert_entity(keeper)
            # Delete others
            other_ids = [r[0] for r in rows[1:]]
            self.conn.execute(
                f"DELETE FROM canonical_entities WHERE id IN ({','.join(['?']*len(other_ids))})",
                other_ids,
            )
            consolidated += 1
        return consolidated

    def find_similar_entities(
        self, normalized_name: str, entityType: str, threshold: float = 0.70
    ) -> List[Tuple[CanonicalEntity, float]]:
        """Find entities with similarity >= threshold"""
        normalized_upper = normalized_name.upper()
        # Fast exact lookup first
        exact = self.get_entity_by_canonical_upper(normalized_upper, entityType)
        if exact:
            return [(exact, 1.0)]

        # Fallback: scan entities of same type
        all_entities = self.get_all_entities_by_type(entityType)
        results = []
        for entity in all_entities:
            score = similarity_score(normalized_upper, entity.canonicalName.upper())
            if score >= threshold:
                results.append((entity, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)

        return results

    def get_all_entities_by_type(self, entityType: str) -> List[CanonicalEntity]:
        """Retrieve all entities of a specific type"""
        rows = self.conn.execute(
            "SELECT * FROM canonical_entities WHERE entityType = ?", [entityType]
        ).fetchall()

        return [self._row_to_entity(row) for row in rows]

    def get_all_entities(self) -> List[CanonicalEntity]:
        """Retrieve all canonical entities for CSV export"""
        rows = self.conn.execute("SELECT * FROM canonical_entities").fetchall()
        return [self._row_to_entity(row) for row in rows]

    def get_entity_by_canonical_upper(self, canonical_upper: str, entityType: str) -> CanonicalEntity | None:
        """Retrieve single entity by UPPER(canonicalName) and entityType (fast exact match)."""
        row = self.conn.execute(
            "SELECT * FROM canonical_entities WHERE entityType = ? AND UPPER(canonicalName) = ? LIMIT 1",
            [entityType, canonical_upper],
        ).fetchone()
        return self._row_to_entity(row) if row else None

    def _row_to_entity(self, row: tuple) -> CanonicalEntity:
        """Convert database row to CanonicalEntity"""
        from src.models.entities import EntityType

        variations_data = json.loads(row[5])
        variations = [
            NameVariation(
                variation_text=v["variation_text"],
                occurrence_count=v["occurrence_count"],
                association_confidence=v["association_confidence"],
                first_seen=datetime.fromisoformat(v["first_seen"]),
                last_seen=datetime.fromisoformat(v["last_seen"]),
            )
            for v in variations_data
        ]

        return CanonicalEntity(
            id=row[0],
            canonicalName=row[1],
            entityType=EntityType(row[2]),
            classification_confidence=self._fix_confidence(row[3]),
            grouping_confidence=row[4],
            variations=variations,
            created_at=row[6],
            updated_at=row[7],
        )

    def export_to_csv(self, output_path: str) -> None:
        """Export entities to CSV format (4 columns: canonicalName, entityType, variations, counts)"""
        entities = self.get_all_entities()

        data = []
        for entity in entities:
            variations_text = ";".join([v.variation_text for v in entity.variations])
            occurrenceCounts = ";".join([str(v.occurrence_count) for v in entity.variations])

            data.append(
                {
                    "canonicalName": entity.canonicalName,
                    "entityType": entity.entityType.value,
                    "variations": variations_text,
                    "occurrenceCounts": occurrenceCounts,
                }
            )

        df = pd.DataFrame(data)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        # Ensure UTF-8 encoding in CSV export with TAB separator, no quotes
        df.to_csv(output_path, index=False, encoding='utf-8', sep='\t', quoting=3)  # QUOTE_NONE

    def export_deduplicated_to_csv(self, output_path: str) -> None:
        """Exportar garantindo que cada (canonicalName, entityType) apareça apenas uma vez.

        Se por qualquer razão ainda houver duplicatas residuais, as variações serão mescladas.
        """
        entities = self.get_all_entities()
        merged: dict[tuple[str, str], CanonicalEntity] = {}
        for e in entities:
            key = (e.canonicalName, e.entityType.value)
            if key not in merged:
                merged[key] = e
            else:
                base = merged[key]
                var_map = {v.variation_text: v for v in base.variations}
                for v in e.variations:
                    if v.variation_text in var_map:
                        existing = var_map[v.variation_text]
                        existing.occurrence_count += v.occurrence_count
                        if v.last_seen > existing.last_seen:
                            existing.last_seen = v.last_seen
                    else:
                        base.variations.append(v)
                base.updated_at = datetime.now()

        data = []
        for entity in merged.values():
            variations_text = ";".join([v.variation_text for v in entity.variations])
            occurrenceCounts = ";".join([str(v.occurrence_count) for v in entity.variations])
            data.append(
                {
                    "canonicalName": entity.canonicalName,
                    "entityType": entity.entityType.value,
                    "variations": variations_text,
                    "occurrenceCounts": occurrenceCounts,
                }
            )
        df = pd.DataFrame(data)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8', sep='\t', quoting=3)

    def close(self) -> None:
        """Close database connection"""
        self.conn.close()
