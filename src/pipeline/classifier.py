"""Classification stage: Identify collector type"""

import re
from typing import Optional
from src.models.contracts import ClassificationInput, ClassificationOutput, ClassificationCategory
from src.pipeline.ner_fallback import NERFallback


class Classifier:
    """Classifier for collector categorization with NER fallback"""

    def __init__(self, use_ner_fallback: bool = True, ner_device: Optional[str] = None):
        """
        Initialize classifier

        Args:
            use_ner_fallback: Enable NER fallback for low-confidence cases (default: True)
            ner_device: Device for NER model ('cuda', 'cpu', or None for auto)
        """
        self.use_ner_fallback = use_ner_fallback
        self.ner_fallback = None
        self.ner_device = ner_device
        self.ner_fallback_count = 0  # Track how many times NER was used

    def classify(self, input_data: ClassificationInput) -> ClassificationOutput:
        """
        Classify collector string into one of 5 categories
        
        Priority order (from research.md):
        1. NãoDeterminado
        2. Empresa
        3. ConjuntoPessoas
        4. Pessoa
        5. GrupoPessoas
        """
        text = input_data.text.strip()
        patterns_matched = []
        
        # 1. Não Determinado (exact matches)
        nao_det_patterns = ["?", "sem coletor", "não identificado", "s.c.", "s/c"]
        if text.lower() in nao_det_patterns:
            return ClassificationOutput(
                original_text=text,
                category=ClassificationCategory.NAO_DETERMINADO,
                confidence=1.0,
                patterns_matched=["exact_match"],
                should_atomize=False
            )
        
        # 2. Empresa/Instituição (all-caps acronyms, institution keywords)
        if re.match(r'^[A-Z]{2,}$', text):  # All caps, 2+ letters
            patterns_matched.append("all_caps_acronym")
            return ClassificationOutput(
                original_text=text,
                category=ClassificationCategory.EMPRESA,
                confidence=0.85,
                patterns_matched=patterns_matched,
                should_atomize=False
            )
        
        # 3. Conjunto de Pessoas (separators + name patterns)
        conjunto_separators = [';', '&', 'et al.', ' e ', ' and ', '|']
        has_separator = any(sep in text for sep in conjunto_separators)
        has_initials = bool(re.search(r'\b[A-Z]\.\s*[A-Z]\.?', text))

        # Check for multiple comma-separated names pattern
        # Pattern: multiple occurrences of "Surname, Initials"
        comma_name_pattern = r'[A-Z][a-z]+,\s*[A-Z]\.'
        comma_matches = re.findall(comma_name_pattern, text)
        has_multiple_comma_names = len(comma_matches) >= 2

        # Check for names with associated numbers (e.g., "I. E. Santo 410, M. F. CASTILHORI 444")
        has_numbers_between_names = bool(re.search(r'[A-Z]\.\s+\d+[,\s]+[A-Z]\.', text))

        # Check for keywords that indicate a group (ALUNOS, etc.)
        group_keywords_in_list = bool(re.search(r',\s*(ALUNOS|EQUIPE|GRUPO)', text, re.IGNORECASE))

        # Check for pattern: "Name & Name" or "Name, Name & Name"
        ampersand_with_names = bool(re.search(r'[A-Z][a-z]+,\s*[A-Z]\.\s*[A-Z]?\.*\s*&', text))

        # Check for multiple short initials/names separated by comma (e.g., "Y. Pires, C. GOMES, E. ADAIS")
        multiple_short_names = len(re.findall(r'[A-Z]\.\s*[A-Z][a-z]+', text)) >= 2

        if (has_separator and has_initials) or has_multiple_comma_names or has_numbers_between_names or group_keywords_in_list or ampersand_with_names or multiple_short_names:
            patterns_matched.extend(["multiple_names", "separator_detected"])
            return ClassificationOutput(
                original_text=text,
                category=ClassificationCategory.CONJUNTO_PESSOAS,
                confidence=0.82,
                patterns_matched=patterns_matched,
                should_atomize=True
            )

        # 4. Pessoa (single name pattern)
        surname_pattern = r'^[A-ZÀ-Ú][a-zà-ú]+(?:-[A-ZÀ-Ú][a-zà-ú]+)?,\s*[A-ZÀ-Ú]\.(?:[A-ZÀ-Ú]\.)*'
        if re.match(surname_pattern, text):
            patterns_matched.append("surname_initials_format")
            return ClassificationOutput(
                original_text=text,
                category=ClassificationCategory.PESSOA,
                confidence=0.80,
                patterns_matched=patterns_matched,
                should_atomize=False
            )

        # Check for initials without strict surname format
        if has_initials and not has_separator:
            patterns_matched.append("single_name_with_initials")
            return ClassificationOutput(
                original_text=text,
                category=ClassificationCategory.PESSOA,
                confidence=0.65,
                patterns_matched=patterns_matched,
                should_atomize=False
            )

        # Discard generic single names (first name or last name only)
        # Pattern: single word, no initials, title case or all caps
        # BUT: Allow single surnames if they have reasonable length (>3 chars) and title case
        if ' ' not in text and ',' not in text and '.' not in text:
            # Check if it's a potential surname (Title case, length > 3)
            # Examples to KEEP: "Cabrera", "Fabris", "Pabst", "Santos"
            # Examples to DISCARD: "A", "Bo", "Sol"
            if len(text) <= 3 or text.isupper() or text.islower():
                patterns_matched.append("generic_single_name")
                return ClassificationOutput(
                    original_text=text,
                    category=ClassificationCategory.NAO_DETERMINADO,
                    confidence=0.0,  # Signal to discard
                    patterns_matched=patterns_matched,
                    should_atomize=False
                )
            # If it passes the filter, treat as low-confidence person name
            patterns_matched.append("single_surname_only")
            return ClassificationOutput(
                original_text=text,
                category=ClassificationCategory.PESSOA,
                confidence=0.55,  # Very low confidence for NER fallback
                patterns_matched=patterns_matched,
                should_atomize=False
            )
        
        # 5. Grupo de Pessoas (generic group terms)
        grupo_keywords = ["pesquisas", "grupo", "equipe", "time", "laboratório", "lab"]
        if any(kw in text.lower() for kw in grupo_keywords):
            patterns_matched.append("group_keyword")
            return ClassificationOutput(
                original_text=text,
                category=ClassificationCategory.GRUPO_PESSOAS,
                confidence=0.70,
                patterns_matched=patterns_matched,
                should_atomize=False
            )

        # Default: Low confidence - use NER fallback
        result = ClassificationOutput(
            original_text=text,
            category=ClassificationCategory.PESSOA,
            confidence=0.60,
            patterns_matched=["default_fallback"],
            should_atomize=False
        )

        # NER fallback for low-confidence cases (threshold raised to 0.85)
        if self.use_ner_fallback and result.confidence < 0.85:
            result = self._apply_ner_fallback(text, result)

        return result

    def _apply_ner_fallback(
        self,
        text: str,
        original_result: ClassificationOutput
    ) -> ClassificationOutput:
        """
        Apply NER fallback to improve low-confidence classification

        Args:
            text: Original text
            original_result: Classification result with confidence < 0.85

        Returns:
            Updated ClassificationOutput with improved confidence or marked for discard
        """
        # Lazy load NER model (only on first use)
        if self.ner_fallback is None:
            self.ner_fallback = NERFallback(device=self.ner_device)

        # Run NER
        ner_output = self.ner_fallback.classify_with_ner(
            text,
            original_result.confidence
        )

        self.ner_fallback_count += 1

        # Check if should discard
        if ner_output.should_discard or ner_output.improved_confidence == 0.0:
            patterns = original_result.patterns_matched.copy()
            patterns.append("ner_discard")
            return ClassificationOutput(
                original_text=text,
                category=ClassificationCategory.NAO_DETERMINADO,
                confidence=0.0,  # Signal to discard
                patterns_matched=patterns,
                should_atomize=False
            )

        # Update category based on NER findings
        category = original_result.category
        patterns = original_result.patterns_matched.copy()
        patterns.append("ner_fallback")

        # Determine category based on entities found
        if ner_output.has_person:
            # Check if multiple persons detected (could be conjunto)
            person_entities = [
                e for e in ner_output.entities
                if e.label in ['PESSOA', 'PER', 'PERSON']
            ]
            if len(person_entities) > 1:
                category = ClassificationCategory.CONJUNTO_PESSOAS
                patterns.append("ner_multiple_persons_detected")
            else:
                category = ClassificationCategory.PESSOA
                patterns.append("ner_person_detected")
        elif ner_output.entities:
            # Check for organization
            has_org = any(
                e.label in ['ORGANIZACAO', 'ORG', 'ORGANIZATION']
                for e in ner_output.entities
            )
            if has_org:
                category = ClassificationCategory.EMPRESA
                patterns.append("ner_org_detected")

        # Return updated result
        return ClassificationOutput(
            original_text=text,
            category=category,
            confidence=ner_output.improved_confidence,
            patterns_matched=patterns,
            should_atomize=(category == ClassificationCategory.CONJUNTO_PESSOAS)
        )
