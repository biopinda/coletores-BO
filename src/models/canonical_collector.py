"""
CanonicalCollector model - Normalized collector identity with grouped variations

This model represents a canonical collector identity that groups multiple
variations under a single normalized form with statistics and metadata.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
import uuid


@dataclass
class CanonicalCollector:
    """Canonical form representing a unique collector identity"""

    # Identity
    canonical_id: str = field(default_factory=lambda: str(uuid.uuid4()))  # Unique identifier (UUID)
    canonical_form: str = ""                      # Chosen representative name
    entity_type: str = ""                         # Classification type
    confidence_score: float = 0.0                 # Overall confidence in canonicalization

    # Name components (for pessoa/conjunto_pessoas types)
    surname_normalized: Optional[str] = None        # Normalized surname
    initials: Optional[Set[str]] = field(default_factory=set)             # Set of initials
    full_names: Optional[Set[str]] = field(default_factory=set)           # Set of known full names

    # Phonetic keys
    phonetic_keys: Dict[str, str] = field(default_factory=dict)           # soundex, metaphone, double_metaphone keys

    # Variations and statistics
    variations: List['CollectorVariation'] = field(default_factory=list)   # All variations grouped under this canonical
    total_occurrences: int = 0                   # Total specimens across all variations
    first_occurrence: Optional[datetime] = None               # Earliest occurrence date
    last_occurrence: Optional[datetime] = None                # Latest occurrence date

    # Kingdom specialization
    kingdom_statistics: Dict[str, 'KingdomStatistics'] = field(default_factory=dict)  # Plantae/Animalia breakdown

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    manual_review_status: str = "none"       # none, pending, approved, rejected
    quality_flags: List[str] = field(default_factory=list)  # Potential issues

    def __post_init__(self):
        """Validate canonical collector"""
        if not self.canonical_form:
            raise ValueError("canonical_form cannot be empty")

        valid_types = [
            "pessoa", "conjunto_pessoas", "grupo_pessoas", "empresa_instituicao"
        ]
        if self.entity_type and self.entity_type not in valid_types:
            raise ValueError(f"Invalid entity_type for canonical: {self.entity_type}")

    def add_variation(self, variation: 'CollectorVariation'):
        """Add a new variation to this canonical collector"""
        from .collector_variation import CollectorVariation  # Import here to avoid circular import

        if not isinstance(variation, CollectorVariation):
            raise ValueError("variation must be a CollectorVariation instance")

        self.variations.append(variation)
        self.total_occurrences += variation.frequency_count

        # Update occurrence date ranges
        if self.first_occurrence is None or (variation.first_occurrence and variation.first_occurrence < self.first_occurrence):
            self.first_occurrence = variation.first_occurrence

        if self.last_occurrence is None or (variation.last_occurrence and variation.last_occurrence > self.last_occurrence):
            self.last_occurrence = variation.last_occurrence

        self.last_updated = datetime.now()

    def get_specialization_score(self) -> Dict[str, float]:
        """Calculate kingdom specialization percentages"""
        total = sum(stats.collection_count for stats in self.kingdom_statistics.values())
        if total == 0:
            return {}
        return {
            kingdom: stats.collection_count / total
            for kingdom, stats in self.kingdom_statistics.items()
        }

    def get_primary_kingdom(self) -> Optional[str]:
        """Get the kingdom where this collector is most active"""
        specialization = self.get_specialization_score()
        if not specialization:
            return None
        return max(specialization.keys(), key=lambda k: specialization[k])

    def is_specialist(self, threshold: float = 0.8) -> bool:
        """Check if collector specializes in one kingdom (>80% by default)"""
        specialization = self.get_specialization_score()
        if not specialization:
            return False
        return max(specialization.values()) > threshold

    def add_quality_flag(self, flag: str):
        """Add a quality concern flag"""
        if flag not in self.quality_flags:
            self.quality_flags.append(flag)
            self.last_updated = datetime.now()

    def remove_quality_flag(self, flag: str):
        """Remove a quality concern flag"""
        if flag in self.quality_flags:
            self.quality_flags.remove(flag)
            self.last_updated = datetime.now()

    def needs_manual_review(self) -> bool:
        """Check if this canonical collector needs manual review"""
        return (self.manual_review_status == "pending" or
                len(self.quality_flags) > 0 or
                self.confidence_score < 0.7)

    def get_variation_texts(self) -> List[str]:
        """Get list of all variation texts"""
        return [var.original_text for var in self.variations]

    def get_most_common_variation(self) -> Optional['CollectorVariation']:
        """Get the most frequently occurring variation"""
        if not self.variations:
            return None
        return max(self.variations, key=lambda v: v.frequency_count)

    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            "canonical_id": self.canonical_id,
            "canonical_form": self.canonical_form,
            "entity_type": self.entity_type,
            "confidence_score": self.confidence_score,
            "surname_normalized": self.surname_normalized,
            "initials": list(self.initials) if self.initials else None,
            "full_names": list(self.full_names) if self.full_names else None,
            "phonetic_keys": self.phonetic_keys,
            "variations": [var.to_dict() for var in self.variations],
            "total_occurrences": self.total_occurrences,
            "first_occurrence": self.first_occurrence,
            "last_occurrence": self.last_occurrence,
            "kingdom_statistics": {k: v.to_dict() for k, v in self.kingdom_statistics.items()},
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "manual_review_status": self.manual_review_status,
            "quality_flags": self.quality_flags,
            "specialization_score": self.get_specialization_score(),
            "primary_kingdom": self.get_primary_kingdom(),
            "is_specialist": self.is_specialist(),
            "needs_manual_review": self.needs_manual_review()
        }

    def __str__(self) -> str:
        """String representation for logging"""
        return f"CanonicalCollector(id={self.canonical_id[:8]}, form='{self.canonical_form}', variations={len(self.variations)}, occurrences={self.total_occurrences})"