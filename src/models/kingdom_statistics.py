"""
KingdomStatistics model - Collector activity breakdown by biological kingdom

This model tracks collector specialization patterns and collection
frequencies across Plantae and Animalia kingdoms.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class KingdomStatistics:
    """Collector activity statistics for a specific biological kingdom"""

    # Kingdom identification
    kingdom: str                             # "Plantae" or "Animalia"

    # Collection metrics
    collection_count: int = 0                # Total collections in this kingdom
    unique_species: int = 0                  # Unique species collected (if available)
    unique_families: int = 0                 # Unique families collected (if available)

    # Temporal distribution
    first_collection: Optional[datetime] = None      # Earliest collection date
    last_collection: Optional[datetime] = None       # Latest collection date
    active_years: List[int] = field(default_factory=list)  # Years with collections

    # Geographic distribution (if available)
    countries: List[str] = field(default_factory=list)     # Countries where collected
    states_provinces: List[str] = field(default_factory=list)  # States/provinces

    # Institution associations
    institutions: Dict[str, int] = field(default_factory=dict)  # Institution -> count

    # Quality metrics
    completeness_score: float = 0.0         # 0-1 score based on data completeness
    reliability_score: float = 0.0          # 0-1 score based on data consistency

    # Metadata
    last_updated: datetime = field(default_factory=datetime.now)

    def __post_init__(self):
        """Validate kingdom statistics"""
        if self.kingdom not in ["Plantae", "Animalia"]:
            raise ValueError(f"Invalid kingdom: {self.kingdom}. Must be 'Plantae' or 'Animalia'")

    def add_collection(self, collection_date: Optional[datetime] = None,
                      institution: Optional[str] = None):
        """Add a collection record to this kingdom's statistics"""
        self.collection_count += 1

        # Update temporal information
        if collection_date:
            if self.first_collection is None or collection_date < self.first_collection:
                self.first_collection = collection_date
            if self.last_collection is None or collection_date > self.last_collection:
                self.last_collection = collection_date

            year = collection_date.year
            if year not in self.active_years:
                self.active_years.append(year)
                self.active_years.sort()

        # Update institution counts
        if institution:
            self.institutions[institution] = self.institutions.get(institution, 0) + 1

        self.last_updated = datetime.now()

    def get_activity_span_years(self) -> Optional[int]:
        """Get number of years between first and last collection"""
        if not self.first_collection or not self.last_collection:
            return None
        return self.last_collection.year - self.first_collection.year + 1

    def get_average_collections_per_year(self) -> float:
        """Calculate average collections per active year"""
        if not self.active_years:
            return 0.0
        return self.collection_count / len(self.active_years)

    def is_active_in_recent_years(self, years: int = 5) -> bool:
        """Check if collector has been active in recent years"""
        if not self.last_collection:
            return False
        current_year = datetime.now().year
        return (current_year - self.last_collection.year) <= years

    def get_primary_institution(self) -> Optional[str]:
        """Get the institution with most collections"""
        if not self.institutions:
            return None
        return max(self.institutions.keys(), key=lambda k: self.institutions[k])

    def get_institutional_diversity(self) -> int:
        """Get number of different institutions associated"""
        return len(self.institutions)

    def calculate_completeness_score(self) -> float:
        """Calculate data completeness score (0-1)"""
        score = 0.0
        total_possible = 7  # Number of completeness factors

        # Factor 1: Has collection count
        if self.collection_count > 0:
            score += 1

        # Factor 2: Has temporal information
        if self.first_collection and self.last_collection:
            score += 1

        # Factor 3: Has multiple years of activity
        if len(self.active_years) > 1:
            score += 1

        # Factor 4: Has institution information
        if self.institutions:
            score += 1

        # Factor 5: Has geographic information
        if self.countries or self.states_provinces:
            score += 1

        # Factor 6: Has taxonomic diversity info
        if self.unique_species > 0 or self.unique_families > 0:
            score += 1

        # Factor 7: Recent activity (shows ongoing work)
        if self.is_active_in_recent_years():
            score += 1

        self.completeness_score = score / total_possible
        return self.completeness_score

    def calculate_reliability_score(self) -> float:
        """Calculate data reliability score (0-1)"""
        score = 0.0
        total_possible = 5

        # Factor 1: Consistent temporal data
        if self.first_collection and self.last_collection and self.first_collection <= self.last_collection:
            score += 1

        # Factor 2: Reasonable collection frequency
        avg_per_year = self.get_average_collections_per_year()
        if 1 <= avg_per_year <= 1000:  # Reasonable range
            score += 1

        # Factor 3: Multiple data sources (institutions)
        if self.get_institutional_diversity() >= 2:
            score += 1

        # Factor 4: Long-term activity (shows sustained work)
        activity_span = self.get_activity_span_years()
        if activity_span and activity_span >= 2:
            score += 1

        # Factor 5: Substantial collection count
        if self.collection_count >= 10:
            score += 1

        self.reliability_score = score / total_possible
        return self.reliability_score

    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            "kingdom": self.kingdom,
            "collection_count": self.collection_count,
            "unique_species": self.unique_species,
            "unique_families": self.unique_families,
            "first_collection": self.first_collection,
            "last_collection": self.last_collection,
            "active_years": self.active_years,
            "countries": self.countries,
            "states_provinces": self.states_provinces,
            "institutions": self.institutions,
            "completeness_score": self.completeness_score,
            "reliability_score": self.reliability_score,
            "last_updated": self.last_updated,
            "activity_span_years": self.get_activity_span_years(),
            "average_collections_per_year": self.get_average_collections_per_year(),
            "is_active_recent": self.is_active_in_recent_years(),
            "primary_institution": self.get_primary_institution(),
            "institutional_diversity": self.get_institutional_diversity()
        }

    def __str__(self) -> str:
        """String representation for logging"""
        return f"KingdomStatistics(kingdom={self.kingdom}, collections={self.collection_count}, years={len(self.active_years)}, institutions={self.get_institutional_diversity()})"