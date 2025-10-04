"""Normalization stage: Standardize name format"""

import re
from src.models.contracts import NormalizationInput, NormalizationOutput


class Normalizer:
    """Normalizer for standardizing name format"""
    
    def normalize(self, input_data: NormalizationInput) -> NormalizationOutput:
        """
        Normalize name: remove extra spaces, standardize punctuation, uppercase
        """
        text = input_data.original_name
        rules_applied = []

        # 1. Remove leading/trailing punctuation and whitespace
        text = re.sub(r'^[.,;:\s]+', '', text)
        text = re.sub(r'[.,;:\s]+$', '', text)
        rules_applied.append("remove_leading_trailing_punct")

        # 2. Remove "et al." and variations (case insensitive)
        text = re.sub(r'\s*et\.?\s*al\.?\s*$', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*et\.?\s*alli\.?\s*$', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s*&\s*et\.?\s*al\.?\s*$', '', text, flags=re.IGNORECASE)
        rules_applied.append("remove_et_al")

        # 3. Remove extra whitespace
        text = ' '.join(text.split())
        rules_applied.append("remove_extra_spaces")

        # 4. Standardize punctuation spacing
        text = re.sub(r'\s*([,;.&])\s*', r'\1 ', text)
        rules_applied.append("standardize_punctuation")

        # 5. Uppercase for comparison
        text = text.upper().strip()
        rules_applied.append("uppercase")

        return NormalizationOutput(
            original=input_data.original_name,
            normalized=text,
            rules_applied=rules_applied
        )
