"""DuckDB-based progress tracker for resumable batch processing"""

import duckdb
from pathlib import Path
from typing import Optional


class ProgressTracker:
    """Track processing progress using DuckDB for efficient handling of millions of records"""

    def __init__(self, db_path: str = "data/progress.duckdb"):
        """Initialize DuckDB connection and create schema"""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = duckdb.connect(str(self.db_path))
        self._create_schema()

    def _create_schema(self) -> None:
        """Create progress tracking table with indexes for fast lookups"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS processed_records (
                record_id VARCHAR PRIMARY KEY,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                batch_number INTEGER
            );
        """)

        # Index for fast lookups
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_record_id
            ON processed_records(record_id);
        """)

        # Index for batch queries
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_batch_number
            ON processed_records(batch_number);
        """)

        # Create metadata table for tracking overall progress
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS progress_metadata (
                key VARCHAR PRIMARY KEY,
                value VARCHAR,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    def is_processed(self, record_id: str) -> bool:
        """Check if record has been processed (optimized for fast lookups)"""
        result = self.conn.execute(
            "SELECT 1 FROM processed_records WHERE record_id = ? LIMIT 1",
            [record_id]
        ).fetchone()
        return result is not None

    def mark_processed(self, record_id: str, batch_number: Optional[int] = None):
        """Mark record as processed"""
        self.conn.execute(
            "INSERT OR IGNORE INTO processed_records (record_id, batch_number) VALUES (?, ?)",
            [record_id, batch_number]
        )

    def mark_batch_processed(self, record_ids: list[str], batch_number: Optional[int] = None):
        """Mark multiple records as processed in a single transaction (much faster)"""
        if not record_ids:
            return

        # Prepare batch insert data
        values = [(record_id, batch_number) for record_id in record_ids]

        self.conn.execute("BEGIN TRANSACTION")
        try:
            self.conn.executemany(
                "INSERT OR IGNORE INTO processed_records (record_id, batch_number) VALUES (?, ?)",
                values
            )
            self.conn.execute("COMMIT")
        except Exception as e:
            self.conn.execute("ROLLBACK")
            raise e

    def get_total_processed(self) -> int:
        """Get total count of processed records"""
        result = self.conn.execute(
            "SELECT COUNT(*) FROM processed_records"
        ).fetchone()
        return result[0] if result else 0

    def get_processed_count_by_batch(self, batch_number: int) -> int:
        """Get count of processed records for a specific batch"""
        result = self.conn.execute(
            "SELECT COUNT(*) FROM processed_records WHERE batch_number = ?",
            [batch_number]
        ).fetchone()
        return result[0] if result else 0

    def reset(self):
        """Reset all progress (for fresh start)"""
        self.conn.execute("DELETE FROM processed_records")
        self.conn.execute("DELETE FROM progress_metadata")

    def set_metadata(self, key: str, value: str):
        """Store metadata about the processing run"""
        self.conn.execute("""
            INSERT OR REPLACE INTO progress_metadata (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, [key, value])

    def get_metadata(self, key: str) -> Optional[str]:
        """Retrieve metadata value"""
        result = self.conn.execute(
            "SELECT value FROM progress_metadata WHERE key = ?",
            [key]
        ).fetchone()
        return result[0] if result else None

    def get_latest_batch_number(self) -> int:
        """Get the highest batch number processed"""
        result = self.conn.execute(
            "SELECT MAX(batch_number) FROM processed_records"
        ).fetchone()
        return result[0] if result and result[0] is not None else 0

    def close(self) -> None:
        """Close database connection"""
        self.conn.close()

    def __enter__(self):
        """Context manager entry"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure connection is closed"""
        self.close()
