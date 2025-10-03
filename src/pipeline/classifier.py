"""Classification stage: Categorize collector strings into 5 types"""

import re
from typing import List

from src.models.entities import ClassificationCategory
from src.models.schemas import ClassificationInput, ClassificationOutput


class Classifier:
    """Classifier for collector name categorization (FR-001 to FR-007)"""

    # Pattern hierarchy from research.md Section 4
    NAO_DETERMINADO_EXACT = {"?", "sem coletor", "nao identificado", "desconhecido"}
    INSTITUTION_KEYWORDS = {
        "embrapa",
        "usp",
        "unicamp",
        "ufrj",
        "ufmg",
        "inpa",
        "jbrj",
        "herbario",
        "jardim botanico",
        "jardim botanico",
        "instituto",
        "universidade",
        "faculdade",
    }
    GROUP_TERMS = {
        "pesquisas",
        "equipe",
        "grupo",
        "projeto",
        "expedicao",
        "levantamento",
    }

    # Regex patterns
    SEPARATOR_PATTERN = re.compile(r"[;&]|et\s+al\.?", re.IGNORECASE)
    ACRONYM_PATTERN = re.compile(r"^[A-Z]{2,}$")
    NAME_WITH_INITIALS = re.compile(
        r"[A-ZÀ-Ž][a-zà-ž]+(?:-[A-ZÀ-Ž][a-zà-ž]+)?,\s*[A-ZÀ-Ž]\.(?:[A-ZÀ-Ž]\.)*"
    )
    INITIALS_PATTERN = re.compile(r"\b[A-ZÀ-Ž]\.[A-ZÀ-Ž]\.?\b")

    def classify(self, input_data: ClassificationInput) -> ClassificationOutput:
        """
        Classify input string into one of 5 categories with confidence score.

        Pattern hierarchy (checked in order):
        1. NaoDeterminado: exact match
        2. Empresa: all-caps acronyms, institution keywords
        3. ConjuntoPessoas: separators + name patterns
        4. Pessoa: single name pattern
        5. GrupoPessoas: generic group terms

        Args:
            input_data: ClassificationInput containing raw text

        Returns:
            ClassificationOutput with category, confidence, and atomization flag

        Raises:
            ValueError: If confidence < 0.70 (below threshold from spec)
        """
        text = input_data.text.strip()
        patterns_matched: List[str] = []
        confidence = 0.0
        category = ClassificationCategory.NAO_DETERMINADO

        # 1. Check for NaoDeterminado (exact match)
        if text.lower() in self.NAO_DETERMINADO_EXACT:
            category = ClassificationCategory.NAO_DETERMINADO
            confidence = 1.0
            patterns_matched.append("exact_nao_determinado")

        # 2. Check for Empresa (all-caps acronyms or institution keywords)
        elif self.ACRONYM_PATTERN.match(text):
            category = ClassificationCategory.EMPRESA
            confidence = 0.90
            patterns_matched.append("acronym")
        elif any(keyword in text.lower() for keyword in self.INSTITUTION_KEYWORDS):
            category = ClassificationCategory.EMPRESA
            confidence = 0.85
            patterns_matched.append("institution_keyword")

        # 3. Check for ConjuntoPessoas (separators + name patterns)
        elif self.SEPARATOR_PATTERN.search(text):
            category = ClassificationCategory.CONJUNTO_PESSOAS
            confidence = 0.90
            patterns_matched.append("multiple_name_separator")

            # Boost confidence if name patterns detected
            if self.NAME_WITH_INITIALS.search(text) or self.INITIALS_PATTERN.search(text):
                confidence = 0.95
                patterns_matched.append("name_pattern_detected")

        # 4. Check for Pessoa (single name pattern)
        elif self.NAME_WITH_INITIALS.search(text) or self.INITIALS_PATTERN.search(text):
            category = ClassificationCategory.PESSOA
            confidence = 0.85
            patterns_matched.append("single_name_pattern")

            # Boost if proper format "Surname, Initials"
            if self.NAME_WITH_INITIALS.search(text):
                confidence = 0.90
                patterns_matched.append("proper_name_format")

        # 5. Check for GrupoPessoas (generic group terms, no proper names)
        elif any(term in text.lower() for term in self.GROUP_TERMS):
            category = ClassificationCategory.GRUPO_PESSOAS
            confidence = 0.75
            patterns_matched.append("group_term")

        # Default fallback if no patterns matched
        else:
            # Try to infer: if has letters but no clear pattern
            if re.search(r"[a-zA-Zà-ž]", text):
                # Ambiguous case - could be Pessoa or GrupoPessoas
                category = ClassificationCategory.PESSOA
                confidence = 0.72
                patterns_matched.append("ambiguous_text")
            else:
                # No letters, likely N�oDeterminado
                category = ClassificationCategory.NAO_DETERMINADO
                confidence = 0.70
                patterns_matched.append("no_letter_pattern")

        # Check threshold
        if confidence < 0.70:
            raise ValueError(
                f"Confidence {confidence:.2f} below threshold (0.70) for text: '{text}'"
            )

        # Determine if should atomize
        should_atomize = category == ClassificationCategory.CONJUNTO_PESSOAS

        return ClassificationOutput(
            original_text=text,
            category=category,
            confidence=confidence,
            patterns_matched=patterns_matched,
            should_atomize=should_atomize,
        )
