"""Atomization stage: Separate ConjuntoPessoas into individual names"""

import re
from typing import List

from src.models.entities import AtomizedName, ClassificationCategory, SeparatorType
from src.models.schemas import AtomizationInput, AtomizationOutput


class Atomizer:
    """Atomizer for splitting conjunto_pessoas strings (FR-008 to FR-010)"""

    def atomize(self, input_data: AtomizationInput) -> AtomizationOutput:
        """
        Separate ConjuntoPessoas strings into individual names.

        Args:
            input_data: AtomizationInput with text and category

        Returns:
            AtomizationOutput with list of atomized names (empty if not ConjuntoPessoas)
        """
        text = input_data.text.strip()
        atomized_names: List[AtomizedName] = []

        # Only atomize if category is ConjuntoPessoas
        if input_data.category != ClassificationCategory.CONJUNTO_PESSOAS:
            return AtomizationOutput(original_text=text, atomized_names=[])

        # Split by separators: ;, &, et al.
        # Strategy: Replace separators with a unique delimiter, then split
        parts = []
        separators_used = []

        # First handle "et al." pattern
        et_al_pattern = re.compile(r"\s*et\s+al\.?\s*", re.IGNORECASE)
        current_text = text

        # Find "et al." occurrences
        et_al_matches = list(et_al_pattern.finditer(current_text))
        if et_al_matches:
            # Split by "et al." and track it
            segments = et_al_pattern.split(current_text)
            for i, segment in enumerate(segments):
                if segment.strip():
                    parts.append((segment.strip(), SeparatorType.ET_AL if i > 0 else None))
        else:
            # No "et al.", process semicolon and ampersand
            # Split by ; first
            semicolon_parts = current_text.split(";")

            for i, semi_part in enumerate(semicolon_parts):
                semi_part = semi_part.strip()
                if not semi_part:
                    continue

                # Now split by &
                ampersand_parts = semi_part.split("&")

                for j, amp_part in enumerate(ampersand_parts):
                    amp_part = amp_part.strip()
                    if not amp_part:
                        continue

                    # Determine separator used
                    if i > 0 and j == 0:
                        # This part came after a semicolon
                        separator = SeparatorType.SEMICOLON
                    elif j > 0:
                        # This part came after an ampersand
                        separator = SeparatorType.AMPERSAND
                    else:
                        # First part
                        separator = None

                    parts.append((amp_part, separator))

        # Create AtomizedName objects
        for position, (name_text, separator) in enumerate(parts):
            if not name_text:
                continue

            atomized_names.append(
                AtomizedName(
                    text=name_text,
                    original_formatting=name_text,
                    position=position,
                    separator_used=separator if separator else SeparatorType.NONE,
                )
            )

        return AtomizationOutput(original_text=text, atomized_names=atomized_names)
