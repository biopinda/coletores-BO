"""
SimilarityScore model - Calculated metric combining surname matching, initial compatibility, and phonetic similarity

This model represents the weighted composite similarity score used for
collector canonicalization based on research findings.
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class SimilarityScore:
    """Calculated similarity score between two collector names"""

    # Component scores (research-based weighting: 50% surname, 30% initials, 20% phonetic)
    surname_similarity: float                # 0.0-1.0 surname match score
    initial_compatibility: float            # 0.0-1.0 initial compatibility score
    phonetic_similarity: float              # 0.0-1.0 phonetic similarity score

    # Composite result
    composite_score: float                   # Final weighted score
    threshold_met: bool                      # True if above canonicalization threshold (0.85)

    # Calculation details
    weighting_scheme: Dict[str, float] = None        # Weighting used in calculation
    algorithm_versions: Dict[str, str] = None        # Algorithm versions used

    # Comparison metadata
    name1_normalized: str = ""               # First name in normalized form
    name2_normalized: str = ""               # Second name in normalized form
    comparison_method: str = "weighted_composite"    # Method used for comparison

    def __post_init__(self):
        """Validate similarity scores and calculate composite if needed"""
        # Validate component scores
        for score_name, score_value in [
            ("surname_similarity", self.surname_similarity),
            ("initial_compatibility", self.initial_compatibility),
            ("phonetic_similarity", self.phonetic_similarity)
        ]:
            if not (0.0 <= score_value <= 1.0):
                raise ValueError(f"{score_name} must be between 0.0 and 1.0, got {score_value}")

        # Set default weighting scheme (research-based)
        if self.weighting_scheme is None:
            self.weighting_scheme = {
                "surname": 0.5,      # 50% - most important for canonicalization
                "initials": 0.3,     # 30% - important for disambiguation
                "phonetic": 0.2      # 20% - helps with variations
            }

        # Calculate composite score if not provided
        if self.composite_score == 0.0:
            self.composite_score = self.calculate_composite_score()

        # Validate composite score
        if not (0.0 <= self.composite_score <= 1.0):
            raise ValueError(f"composite_score must be between 0.0 and 1.0, got {self.composite_score}")

        # Determine if threshold met (research recommendation: 0.85)
        self.threshold_met = self.composite_score >= 0.85

        # Set default algorithm versions
        if self.algorithm_versions is None:
            self.algorithm_versions = {
                "surname": "jaro_winkler",      # Research decision: Jaro-Winkler for performance
                "phonetic": "double_metaphone", # Research decision: Double Metaphone via Jellyfish
                "composite": "weighted_average"
            }

    def calculate_composite_score(self) -> float:
        """Calculate weighted composite similarity score"""
        return (
            self.weighting_scheme["surname"] * self.surname_similarity +
            self.weighting_scheme["initials"] * self.initial_compatibility +
            self.weighting_scheme["phonetic"] * self.phonetic_similarity
        )

    def meets_manual_review_threshold(self, threshold: float = 0.5) -> bool:
        """Check if similarity is below manual review threshold"""
        return self.composite_score < threshold

    def get_quality_level(self) -> str:
        """Get quality assessment based on composite score"""
        if self.composite_score >= 0.95:
            return "excellent"
        elif self.composite_score >= 0.85:
            return "high"
        elif self.composite_score >= 0.7:
            return "medium"
        elif self.composite_score >= 0.5:
            return "low"
        else:
            return "very_low"

    def get_primary_matching_factor(self) -> str:
        """Identify which component contributed most to the match"""
        scores = {
            "surname": self.surname_similarity * self.weighting_scheme["surname"],
            "initials": self.initial_compatibility * self.weighting_scheme["initials"],
            "phonetic": self.phonetic_similarity * self.weighting_scheme["phonetic"]
        }
        return max(scores.keys(), key=lambda k: scores[k])

    def is_strong_match(self) -> bool:
        """Check if this represents a strong similarity match"""
        return self.composite_score >= 0.9

    def is_weak_match(self) -> bool:
        """Check if this represents a weak similarity match"""
        return self.composite_score < 0.6

    def requires_human_verification(self) -> bool:
        """Check if similarity score requires human verification"""
        # Require verification for borderline cases or conflicting signals
        if 0.7 <= self.composite_score <= 0.9:
            return True

        # Also require verification if component scores are highly divergent
        component_scores = [self.surname_similarity, self.initial_compatibility, self.phonetic_similarity]
        score_range = max(component_scores) - min(component_scores)
        return score_range > 0.5

    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            "surname_similarity": self.surname_similarity,
            "initial_compatibility": self.initial_compatibility,
            "phonetic_similarity": self.phonetic_similarity,
            "composite_score": self.composite_score,
            "threshold_met": self.threshold_met,
            "weighting_scheme": self.weighting_scheme,
            "algorithm_versions": self.algorithm_versions,
            "name1_normalized": self.name1_normalized,
            "name2_normalized": self.name2_normalized,
            "comparison_method": self.comparison_method,
            "quality_level": self.get_quality_level(),
            "primary_matching_factor": self.get_primary_matching_factor(),
            "is_strong_match": self.is_strong_match(),
            "requires_human_verification": self.requires_human_verification()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SimilarityScore':
        """Create SimilarityScore from dictionary"""
        return cls(
            surname_similarity=data["surname_similarity"],
            initial_compatibility=data["initial_compatibility"],
            phonetic_similarity=data["phonetic_similarity"],
            composite_score=data.get("composite_score", 0.0),
            threshold_met=data.get("threshold_met", False),
            weighting_scheme=data.get("weighting_scheme"),
            algorithm_versions=data.get("algorithm_versions"),
            name1_normalized=data.get("name1_normalized", ""),
            name2_normalized=data.get("name2_normalized", ""),
            comparison_method=data.get("comparison_method", "weighted_composite")
        )

    def __str__(self) -> str:
        """String representation for logging"""
        return f"SimilarityScore(composite={self.composite_score:.3f}, surname={self.surname_similarity:.3f}, initials={self.initial_compatibility:.3f}, phonetic={self.phonetic_similarity:.3f}, quality={self.get_quality_level()})"