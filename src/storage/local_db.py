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

    def _create_schema(self) -> None:
        """Create canonical_entities table with schema from data-model.md"""
        # Create sequence for ID
        self.conn.execute("CREATE SEQUENCE IF NOT EXISTS canonical_entities_id_seq")

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS canonical_entities (
                id INTEGER PRIMARY KEY DEFAULT nextval('canonical_entities_id_seq'),
                canonical_name TEXT NOT NULL,
                entity_type TEXT NOT NULL CHECK(entity_type IN ('Pessoa', 'GrupoPessoas', 'Empresa', 'NaoDeterminado')),
                classification_confidence REAL NOT NULL CHECK(classification_confidence >= 0.70 AND classification_confidence <= 1.0),
                grouping_confidence REAL NOT NULL CHECK(grouping_confidence >= 0.70 AND grouping_confidence <= 1.0),
                variations JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        self.conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_canonical_name_type ON canonical_entities(canonical_name, entity_type)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_entity_type ON canonical_entities(entity_type)"
        )

    def upsert_entity(self, entity: CanonicalEntity) -> CanonicalEntity:
        """Insert new or update existing canonical entity"""
        # Serialize variations to JSON
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
            ]
        )

        if entity.id is None:
            # Insert new entity
            result = self.conn.execute(
                """
                INSERT INTO canonical_entities
                (canonical_name, entity_type, classification_confidence, grouping_confidence,
                 variations, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                RETURNING id
                """,
                [
                    entity.canonical_name,
                    entity.entity_type.value,
                    entity.classification_confidence,
                    entity.grouping_confidence,
                    variations_json,
                    entity.created_at,
                    entity.updated_at,
                ],
            ).fetchone()
            entity.id = result[0]
        else:
            # Update existing entity
            self.conn.execute(
                """
                UPDATE canonical_entities
                SET canonical_name = ?, entity_type = ?, classification_confidence = ?,
                    grouping_confidence = ?, variations = ?, updated_at = ?
                WHERE id = ?
                """,
                [
                    entity.canonical_name,
                    entity.entity_type.value,
                    entity.classification_confidence,
                    entity.grouping_confidence,
                    variations_json,
                    entity.updated_at,
                    entity.id,
                ],
            )

        return entity

    def find_similar_entities(
        self, normalized_name: str, entity_type: str, threshold: float = 0.70
    ) -> List[Tuple[CanonicalEntity, float]]:
        """Find entities with similarity >= threshold"""
        # Load all entities of the same type
        all_entities = self.get_all_entities_by_type(entity_type)

        # Calculate similarity scores
        results = []
        for entity in all_entities:
            # Compare with canonical name
            score = similarity_score(normalized_name, entity.canonical_name)

            if score >= threshold:
                results.append((entity, score))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)

        return results

    def get_all_entities_by_type(self, entity_type: str) -> List[CanonicalEntity]:
        """Retrieve all entities of a specific type"""
        rows = self.conn.execute(
            "SELECT * FROM canonical_entities WHERE entity_type = ?", [entity_type]
        ).fetchall()

        return [self._row_to_entity(row) for row in rows]

    def get_all_entities(self) -> List[CanonicalEntity]:
        """Retrieve all canonical entities for CSV export"""
        rows = self.conn.execute("SELECT * FROM canonical_entities").fetchall()
        return [self._row_to_entity(row) for row in rows]

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
            canonical_name=row[1],
            entity_type=EntityType(row[2]),
            classification_confidence=row[3],
            grouping_confidence=row[4],
            variations=variations,
            created_at=row[6],
            updated_at=row[7],
        )

    def export_to_csv(self, output_path: str) -> None:
        """Export entities to CSV format (3 columns: canonical_name, variations, counts)"""
        entities = self.get_all_entities()

        data = []
        for entity in entities:
            variations_text = ";".join([v.variation_text for v in entity.variations])
            occurrence_counts = ";".join([str(v.occurrence_count) for v in entity.variations])

            data.append(
                {
                    "canonical_name": entity.canonical_name,
                    "variations": variations_text,
                    "occurrence_counts": occurrence_counts,
                }
            )

        df = pd.DataFrame(data)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(output_path, index=False)

    def close(self) -> None:
        """Close database connection"""
        self.conn.close()
