"""Normalization stage: Standardize names for comparison"""

import re
from typing import List

from src.models.schemas import NormalizationInput, NormalizationOutput


class Normalizer:
    """Normalizer for name standardization (FR-011, FR-012)"""

    def normalize(self, input_data: NormalizationInput) -> NormalizationOutput:
        """
        Normalize name: remove extra spaces, standardize punctuation, uppercase.

        Rules from research.md Section 1:
        1. Remove extra whitespace
        2. Standardize punctuation spacing
        3. Uppercase for comparison

        Args:
            input_data: NormalizationInput with original name

        Returns:
            NormalizationOutput with normalized name and rules applied
        """
        original = input_data.original_name
        rules_applied: List[str] = []

        # Start with the original text
        normalized = original

        # Rule 1: Remove extra whitespace
        if "  " in normalized or normalized != normalized.strip():
            normalized = " ".join(normalized.split())
            rules_applied.append("remove_extra_spaces")

        # Rule 2: Standardize punctuation spacing
        # Ensure punctuation marks are followed by a space
        before_punctuation = normalized
        normalized = re.sub(r"\s*([,;.&])\s*", r"\1 ", normalized)
        normalized = normalized.strip()

        if before_punctuation != normalized:
            rules_applied.append("standardize_punctuation")

        # Rule 3: Uppercase for comparison
        if normalized != normalized.upper():
            normalized = normalized.upper()
            rules_applied.append("uppercase")

        return NormalizationOutput(
            original=original, normalized=normalized, rules_applied=rules_applied
        )
