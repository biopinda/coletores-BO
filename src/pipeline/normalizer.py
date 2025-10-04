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

        # Rule 1: Trim obvious leading separator characters and punctuation (ex: leading ';', ',', '&', '.')
        stripped_initial = re.sub(r'^[;,&.\s]+', '', normalized)
        if stripped_initial != normalized:
            normalized = stripped_initial
            rules_applied.append("remove_leading_separators")

        # Rule 2: Remove trailing separator clutter
        stripped_trailing = re.sub(r'[;,&\s]+$', '', normalized)
        if stripped_trailing != normalized:
            normalized = stripped_trailing
            rules_applied.append("remove_trailing_separators")

        # Rule 3: Remove extra whitespace
        if "  " in normalized or normalized != normalized.strip():
            normalized = " ".join(normalized.split())
            rules_applied.append("remove_extra_spaces")

        # Rule 4: Standardize punctuation spacing
        # Ensure punctuation marks are followed by a space
        before_punctuation = normalized
        normalized = re.sub(r"\s*([,;.&])\s*", r"\1 ", normalized)
        normalized = normalized.strip()

        if before_punctuation != normalized:
            rules_applied.append("standardize_punctuation")

        # Rule 5: Uppercase for comparison
        if normalized != normalized.upper():
            normalized = normalized.upper()
            rules_applied.append("uppercase")

        # Rule 6: Remover novamente separadores iniciais residuais pós transformações
        cleaned = re.sub(r'^[;\s]+', '', normalized)
        if cleaned != normalized:
            normalized = cleaned
            rules_applied.append("strip_leading_separators_post")

        # Rule 7: Se nome começa com 'E ' (português 'e' conjuntivo errante no início) remover
        if normalized.startswith('E '):
            normalized = normalized[2:]
            rules_applied.append("remove_leading_conjunction_e")

        # Rule 8: Remove parenthetical observations like (Pai), (Irmão), (Tziu)
        before_parens = normalized
        normalized = re.sub(r'\s*\([^)]*\)\s*', ' ', normalized)
        normalized = normalized.strip()
        if before_parens != normalized:
            rules_applied.append("remove_parenthetical_observations")

        # Rule 9: Normalize initials - remove spaces between initials
        # "I. R." -> "I.R." for better similarity matching (Andrade, I. R. = Andrade, I.R.)
        before_initials = normalized
        # Match pattern: capital letter + dot + spaces + another capital (likely an initial)
        normalized = re.sub(r'([A-Z]\.)\s+(?=[A-Z]\.)', r'\1', normalized)
        if before_initials != normalized:
            rules_applied.append("normalize_initial_spacing")

        return NormalizationOutput(
            original=original, normalized=normalized, rules_applied=rules_applied
        )
