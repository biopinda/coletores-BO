"""
CollectorVariation model - Individual form of collector name with occurrence data

This model represents a specific variation of a collector name with
frequency data and occurrence statistics.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import uuid


@dataclass
class CollectorVariation:
    """Specific variation of a collector name"""

    # Identity
    variation_id: str = field(default_factory=lambda: str(uuid.uuid4()))     # Unique identifier
    original_text: str = ""                       # Exact text from recordedBy field
    normalized_text: str = ""                     # Normalized form for comparison

    # Occurrence data
    frequency_count: int = 0                      # Number of times this variation appears
    first_occurrence: Optional[datetime] = None  # Earliest occurrence date
    last_occurrence: Optional[datetime] = None   # Latest occurrence date

    # Source tracking
    source_documents: List[str] = field(default_factory=list)  # MongoDB document IDs
    datasets: List[str] = field(default_factory=list)          # Source datasets
    institutions: List[str] = field(default_factory=list)      # Contributing institutions

    # Kingdom breakdown
    kingdom_counts: Dict[str, int] = field(default_factory=dict)  # Plantae/Animalia counts

    # Quality metrics
    similarity_scores: Dict[str, float] = field(default_factory=dict)  # Similarity to canonical form
    confidence_score: float = 0.0                # Confidence in this variation assignment

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate variation"""
        if not self.original_text:
            raise ValueError("original_text cannot be empty")

        if not self.normalized_text:
            self.normalized_text = self.original_text.strip().lower()

    def add_occurrence(self, document_id: str, kingdom: str, occurrence_date: Optional[datetime] = None,
                      dataset: Optional[str] = None, institution: Optional[str] = None):
        """Add a new occurrence of this variation"""
        self.frequency_count += 1

        # Track source
        if document_id not in self.source_documents:
            self.source_documents.append(document_id)

        # Update kingdom counts
        self.kingdom_counts[kingdom] = self.kingdom_counts.get(kingdom, 0) + 1

        # Update occurrence dates
        if occurrence_date:
            if self.first_occurrence is None or occurrence_date < self.first_occurrence:
                self.first_occurrence = occurrence_date
            if self.last_occurrence is None or occurrence_date > self.last_occurrence:
                self.last_occurrence = occurrence_date

        # Track datasets and institutions
        if dataset and dataset not in self.datasets:
            self.datasets.append(dataset)
        if institution and institution not in self.institutions:
            self.institutions.append(institution)

        self.last_updated = datetime.now()

    def get_kingdom_percentage(self, kingdom: str) -> float:
        """Get percentage of occurrences in specified kingdom"""
        if self.frequency_count == 0:
            return 0.0
        return self.kingdom_counts.get(kingdom, 0) / self.frequency_count

    def get_primary_kingdom(self) -> Optional[str]:
        """Get the kingdom where this variation appears most"""
        if not self.kingdom_counts:
            return None
        return max(self.kingdom_counts.keys(), key=lambda k: self.kingdom_counts[k])

    def is_kingdom_specialist(self, threshold: float = 0.8) -> bool:
        """Check if variation appears primarily in one kingdom"""
        if not self.kingdom_counts:
            return False
        primary_count = max(self.kingdom_counts.values())
        return primary_count / self.frequency_count > threshold

    def get_activity_span_days(self) -> Optional[int]:
        """Get number of days between first and last occurrence"""
        if not self.first_occurrence or not self.last_occurrence:
            return None
        return (self.last_occurrence - self.first_occurrence).days

    def is_recent(self, days: int = 365) -> bool:
        """Check if variation has recent activity"""
        if not self.last_occurrence:
            return False
        return (datetime.now() - self.last_occurrence).days <= days

    def is_historical(self, years: int = 10) -> bool:
        """Check if variation is primarily historical"""
        if not self.last_occurrence:
            return False
        return (datetime.now() - self.last_occurrence).days > (years * 365)

    def add_similarity_score(self, comparison_type: str, score: float):
        """Add similarity score for comparison to canonical or other variations"""
        if not (0.0 <= score <= 1.0):
            raise ValueError(f"Similarity score must be between 0.0 and 1.0, got {score}")
        self.similarity_scores[comparison_type] = score
        self.last_updated = datetime.now()

    def get_quality_assessment(self) -> str:
        """Get overall quality assessment of this variation"""
        if self.frequency_count >= 100:
            return "high_frequency"
        elif self.frequency_count >= 10:
            return "medium_frequency"
        elif self.frequency_count >= 2:
            return "low_frequency"
        else:
            return "single_occurrence"

    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            "variation_id": self.variation_id,
            "original_text": self.original_text,
            "normalized_text": self.normalized_text,
            "frequency_count": self.frequency_count,
            "first_occurrence": self.first_occurrence,
            "last_occurrence": self.last_occurrence,
            "source_documents": self.source_documents,
            "datasets": self.datasets,
            "institutions": self.institutions,
            "kingdom_counts": self.kingdom_counts,
            "similarity_scores": self.similarity_scores,
            "confidence_score": self.confidence_score,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "primary_kingdom": self.get_primary_kingdom(),
            "kingdom_specialist": self.is_kingdom_specialist(),
            "activity_span_days": self.get_activity_span_days(),
            "quality_assessment": self.get_quality_assessment()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'CollectorVariation':
        """Create CollectorVariation from dictionary"""
        variation = cls(
            variation_id=data.get("variation_id", str(uuid.uuid4())),
            original_text=data["original_text"],
            normalized_text=data.get("normalized_text", ""),
            frequency_count=data.get("frequency_count", 0),
            first_occurrence=data.get("first_occurrence"),
            last_occurrence=data.get("last_occurrence"),
            source_documents=data.get("source_documents", []),
            datasets=data.get("datasets", []),
            institutions=data.get("institutions", []),
            kingdom_counts=data.get("kingdom_counts", {}),
            similarity_scores=data.get("similarity_scores", {}),
            confidence_score=data.get("confidence_score", 0.0),
            created_at=data.get("created_at", datetime.now()),
            last_updated=data.get("last_updated", datetime.now())
        )
        return variation

    def __str__(self) -> str:
        """String representation for logging"""
        return f"CollectorVariation(text='{self.original_text}', freq={self.frequency_count}, primary_kingdom={self.get_primary_kingdom()})"