"""Local database (DuckDB) for canonical entities storage"""

import duckdb
from typing import List, Tuple
from ..models.entities import CanonicalEntity


class LocalDatabase:
    """DuckDB database for storing canonical entities"""

    def __init__(self, db_path: str):
        """Initialize database connection and create schema"""
        self.db_path = db_path
        self.conn = duckdb.connect(db_path)
        self._create_schema()

    def _create_schema(self) -> None:
        """Create canonical_entities table with proper schema"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS canonical_entities (
                id INTEGER PRIMARY KEY,
                canonicalName TEXT NOT NULL,
                entityType TEXT NOT NULL CHECK(entityType IN ('Pessoa', 'GrupoPessoas', 'Empresa', 'NaoDeterminado')),
                classification_confidence REAL NOT NULL CHECK(classification_confidence >= 0.70 AND classification_confidence <= 1.0),
                grouping_confidence REAL NOT NULL CHECK(grouping_confidence >= 0.70 AND grouping_confidence <= 1.0),
                variations JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        self.conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_canonicalName_type 
            ON canonical_entities(canonicalName, entityType);
        """)

        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_entityType 
            ON canonical_entities(entityType);
        """)

    def upsert_entity(self, entity: CanonicalEntity) -> CanonicalEntity:
        """Insert new or update existing canonical entity"""
        import json

        variations_json = json.dumps([v.model_dump() for v in entity.variations], default=str)

        # Check if entity already exists
        existing = self.conn.execute("""
            SELECT id FROM canonical_entities
            WHERE canonicalName = ? AND entityType = ?
        """, [entity.canonicalName, entity.entityType.value]).fetchone()

        if existing:
            # Update existing entity
            self.conn.execute("""
                UPDATE canonical_entities SET
                    classification_confidence = ?,
                    grouping_confidence = ?,
                    variations = ?,
                    updated_at = ?
                WHERE canonicalName = ? AND entityType = ?
            """, [
                entity.classification_confidence,
                entity.grouping_confidence,
                variations_json,
                entity.updated_at,
                entity.canonicalName,
                entity.entityType.value
            ])
            entity.id = existing[0]
        else:
            # Insert new entity - DuckDB doesn't support AUTOINCREMENT in the same way
            # Get the next ID manually
            max_id_result = self.conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM canonical_entities").fetchone()
            next_id = max_id_result[0] if max_id_result else 1

            self.conn.execute("""
                INSERT INTO canonical_entities
                (id, canonicalName, entityType, classification_confidence, grouping_confidence,
                 variations, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                next_id,
                entity.canonicalName,
                entity.entityType.value,
                entity.classification_confidence,
                entity.grouping_confidence,
                variations_json,
                entity.created_at,
                entity.updated_at
            ])
            entity.id = next_id

        return entity

    def find_similar_entities(
        self,
        normalized_name: str,
        entityType: str,
        threshold: float = 0.70
    ) -> List[Tuple[CanonicalEntity, float]]:
        """Find entities with similarity >= threshold, return with scores"""
        from ..algorithms.similarity import similarity_score as calc_similarity
        import json
        from datetime import datetime

        # Get all entities of same type
        results = self.conn.execute("""
            SELECT id, canonicalName, entityType, classification_confidence,
                   grouping_confidence, variations, created_at, updated_at
            FROM canonical_entities
            WHERE entityType = ?
        """, [entityType]).fetchall()

        similar_entities = []

        for row in results:
            canon_name = row[1]
            similarity = calc_similarity(normalized_name, canon_name)

            if similarity >= threshold:
                # Reconstruct entity
                variations_data = json.loads(row[5])
                from ..models.contracts import CanonicalVariation, EntityType

                variations = [
                    CanonicalVariation(
                        variation_text=v['variation_text'],
                        occurrence_count=v['occurrence_count'],
                        association_confidence=v['association_confidence'],
                        first_seen=datetime.fromisoformat(v['first_seen']) if isinstance(v['first_seen'], str) else v['first_seen'],
                        last_seen=datetime.fromisoformat(v['last_seen']) if isinstance(v['last_seen'], str) else v['last_seen']
                    )
                    for v in variations_data
                ]

                entity = CanonicalEntity(
                    id=row[0],
                    canonicalName=row[1],
                    entityType=EntityType(row[2]),
                    classification_confidence=row[3],
                    grouping_confidence=row[4],
                    variations=variations,
                    created_at=row[6],
                    updated_at=row[7]
                )

                similar_entities.append((entity, similarity))

        # Sort by similarity (highest first)
        similar_entities.sort(key=lambda x: x[1], reverse=True)

        return similar_entities

    def get_all_entities(self) -> List[CanonicalEntity]:
        """Retrieve all canonical entities"""
        import json
        from datetime import datetime
        from ..models.contracts import CanonicalVariation, EntityType

        results = self.conn.execute("""
            SELECT id, canonicalName, entityType, classification_confidence,
                   grouping_confidence, variations, created_at, updated_at
            FROM canonical_entities
        """).fetchall()

        entities = []
        for row in results:
            variations_data = json.loads(row[5])

            variations = [
                CanonicalVariation(
                    variation_text=v['variation_text'],
                    occurrence_count=v['occurrence_count'],
                    association_confidence=v['association_confidence'],
                    first_seen=datetime.fromisoformat(v['first_seen']) if isinstance(v['first_seen'], str) else v['first_seen'],
                    last_seen=datetime.fromisoformat(v['last_seen']) if isinstance(v['last_seen'], str) else v['last_seen']
                )
                for v in variations_data
            ]

            entity = CanonicalEntity(
                id=row[0],
                canonicalName=row[1],
                entityType=EntityType(row[2]),
                classification_confidence=row[3],
                grouping_confidence=row[4],
                variations=variations,
                created_at=row[6],
                updated_at=row[7]
            )
            entities.append(entity)

        return entities

    def export_to_csv(self, output_path: str) -> None:
        """Export entities to CSV format"""
        import pandas as pd

        entities = self.get_all_entities()

        rows = []
        for entity in entities:
            variations_text = ";".join([v.variation_text for v in entity.variations])
            occurrence_counts = ";".join([str(v.occurrence_count) for v in entity.variations])

            rows.append({
                "canonicalName": entity.canonicalName,
                "variations": variations_text,
                "occurrenceCounts": occurrence_counts
            })

        df = pd.DataFrame(rows)
        df.to_csv(output_path, index=False)

    def close(self) -> None:
        """Close database connection"""
        self.conn.close()
