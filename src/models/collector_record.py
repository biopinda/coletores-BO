"""
CollectorRecord model - Individual specimen record from MongoDB collection

This model represents source specimen records containing collector information
from the MongoDB 'ocorrencias' collection, supporting 11M+ record processing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from bson import ObjectId


@dataclass
class CollectorRecord:
    """Individual specimen record from MongoDB collection"""

    # Primary identifiers
    document_id: ObjectId                    # MongoDB _id
    recorded_by: str                         # Original recordedBy string
    kingdom: str                             # Biological kingdom (Plantae/Animalia)

    # Occurrence metadata
    occurrence_id: Optional[str] = None             # Specimen occurrence identifier
    collection_date: Optional[datetime] = None      # When specimen was collected
    dataset_name: Optional[str] = None              # Source dataset
    institution_code: Optional[str] = None          # Institution responsible

    # Processing metadata
    created_at: datetime = field(default_factory=datetime.now)     # Record creation timestamp
    last_modified: datetime = field(default_factory=datetime.now)  # Last modification timestamp
    processing_status: str = "pending"                             # pending, processed, error, manual_review
    processing_errors: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate required fields and normalize data"""
        if not self.recorded_by or not self.recorded_by.strip():
            raise ValueError("recorded_by cannot be empty")
        if self.kingdom not in ["Plantae", "Animalia"]:
            raise ValueError(f"Invalid kingdom: {self.kingdom}")

        # Normalize recorded_by (strip whitespace, ensure consistent encoding)
        self.recorded_by = self.recorded_by.strip()

    def mark_processed(self):
        """Mark record as successfully processed"""
        self.processing_status = "processed"
        self.last_modified = datetime.now()

    def mark_error(self, error_message: str):
        """Mark record as having processing error"""
        self.processing_status = "error"
        self.processing_errors.append(error_message)
        self.last_modified = datetime.now()

    def mark_manual_review(self, reason: str):
        """Mark record for manual review"""
        self.processing_status = "manual_review"
        self.processing_errors.append(f"Manual review required: {reason}")
        self.last_modified = datetime.now()

    def to_dict(self) -> dict:
        """Convert to dictionary for MongoDB storage"""
        return {
            "_id": self.document_id,
            "recordedBy": self.recorded_by,
            "kingdom": self.kingdom,
            "occurrenceID": self.occurrence_id,
            "eventDate": self.collection_date,
            "datasetName": self.dataset_name,
            "institutionCode": self.institution_code,
            "created_at": self.created_at,
            "last_modified": self.last_modified,
            "processing_status": self.processing_status,
            "processing_errors": self.processing_errors
        }

    @classmethod
    def from_mongodb_doc(cls, doc: dict) -> 'CollectorRecord':
        """Create CollectorRecord from MongoDB document"""
        return cls(
            document_id=doc.get("_id"),
            recorded_by=doc.get("recordedBy", ""),
            kingdom=doc.get("kingdom", "Unknown"),
            occurrence_id=doc.get("occurrenceID"),
            collection_date=doc.get("eventDate"),
            dataset_name=doc.get("datasetName"),
            institution_code=doc.get("institutionCode"),
            created_at=doc.get("created_at", datetime.now()),
            last_modified=doc.get("last_modified", datetime.now()),
            processing_status=doc.get("processing_status", "pending"),
            processing_errors=doc.get("processing_errors", [])
        )

    def __str__(self) -> str:
        """String representation for logging"""
        return f"CollectorRecord(id={self.document_id}, recorded_by='{self.recorded_by}', kingdom={self.kingdom})"