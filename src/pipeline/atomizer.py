"""Atomization stage: Separate conjunto de pessoas into individual names"""

import re
from src.models.contracts import (
    AtomizationInput,
    AtomizationOutput,
    AtomizedName,
    ClassificationCategory,
    SeparatorType
)


class Atomizer:
    """Atomizer for separating multiple names"""
    
    def atomize(self, input_data: AtomizationInput) -> AtomizationOutput:
        """
        Separate ConjuntoPessoas into individual names
        Returns empty list if not ConjuntoPessoas
        """
        if input_data.category != ClassificationCategory.CONJUNTO_PESSOAS:
            return AtomizationOutput(
                original_text=input_data.text,
                atomized_names=[]
            )
        
        text = input_data.text
        atomized_names = []
        
        # Split by separators (priority order)
        parts = []
        current_sep = SeparatorType.NONE
        
        # Handle "et al." first (special case)
        if 'et al.' in text:
            parts_et_al = text.split('et al.')
            text = parts_et_al[0].strip()
            current_sep = SeparatorType.ET_AL
        
        # Split by semicolon
        if ';' in text:
            parts = text.split(';')
            current_sep = SeparatorType.SEMICOLON
        # Split by ampersand
        elif '&' in text:
            parts = text.split('&')
            current_sep = SeparatorType.AMPERSAND
        # Split by " e " or " and "
        elif ' e ' in text.lower():
            parts = re.split(r'\s+e\s+', text, flags=re.IGNORECASE)
            current_sep = SeparatorType.AMPERSAND
        elif ' and ' in text.lower():
            parts = re.split(r'\s+and\s+', text, flags=re.IGNORECASE)
            current_sep = SeparatorType.AMPERSAND
        else:
            parts = [text]
        
        # Create AtomizedName objects
        for i, part in enumerate(parts):
            part = part.strip()
            if part:
                atomized_names.append(AtomizedName(
                    text=part,
                    original_formatting=part,
                    position=i,
                    separator_used=current_sep if i > 0 else SeparatorType.NONE
                ))
        
        return AtomizationOutput(
            original_text=input_data.text,
            atomized_names=atomized_names
        )
