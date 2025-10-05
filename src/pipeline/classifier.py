"""Classification stage: Identify collector type"""

import re
from typing import Optional
from src.models.contracts import ClassificationInput, ClassificationOutput, ClassificationCategory
from src.pipeline.ner_fallback import NERFallback


class Classifier:
    """Classifier for collector categorization with NER fallback"""

    def __init__(self, use_ner_fallback: bool = True, ner_device: Optional[str] = None, ner_model: str = "lenerbr"):
        """
        Initialize classifier

        Args:
            use_ner_fallback: Enable NER fallback for low-confidence cases (default: True)
            ner_device: Device for NER model ('cuda', 'cpu', or None for auto)
            ner_model: NER model to use (lenerbr, bertimbau-base, bertimbau-large, bertimbau-ner, multilingual)
        """
        self.use_ner_fallback = use_ner_fallback
        self.ner_fallback = None
        self.ner_device = ner_device
        self.ner_model = ner_model
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
        # Sanitize trailing collection / specimen codes like "(67)", "1007", "1092A" at the END only
        sanitized_text, had_trailing_code = self._sanitize_trailing_codes(text)
        # Keep both original and sanitized for downstream use
        working_text = sanitized_text if had_trailing_code else text
        patterns_matched = []

        # 1. Não Determinado (exact matches)
        nao_det_patterns = ["?", "sem coletor", "não identificado", "s.c.", "s/c"]
        if working_text.lower() in nao_det_patterns:
            return ClassificationOutput(
                original_text=text,
                sanitized_text=working_text,
                category=ClassificationCategory.NAO_DETERMINADO,
                confidence=1.0,
                patterns_matched=["exact_match"],
                should_atomize=False
            )
        
        # 2. Empresa/Instituição (all-caps acronyms, institution keywords)
        if re.match(r'^[A-Z]{2,}$', working_text):  # All caps, 2+ letters
            patterns_matched.append("all_caps_acronym")
            return ClassificationOutput(
                original_text=text,
                sanitized_text=working_text,
                category=ClassificationCategory.EMPRESA,
                confidence=0.85,
                patterns_matched=patterns_matched,
                should_atomize=False
            )
        
        # 3. Conjunto de Pessoas (separators + name patterns)
        conjunto_separators = [';', '&', 'et al.', ' e ', ' and ', '|']
        has_separator = any(sep in working_text for sep in conjunto_separators)
        has_initials = bool(re.search(r'\b[A-Z]\.\s*[A-Z]\.?', working_text))

        # Check for multiple comma-separated names pattern
        # Pattern: multiple occurrences of "Surname, Initials" or "Initials Surname"
        comma_name_pattern = r'[A-Z][a-z]+,\s*[A-Z]\.'
        comma_matches = re.findall(comma_name_pattern, working_text)
        has_multiple_comma_names = len(comma_matches) >= 2

        # Check for multiple initials+surname patterns separated by comma
        # Examples: "A. O. Scariot, A. C. SEVILHA", "A. S. Rodrigues, G. PEREIRA-SILVA"
        initials_surname_pattern = r'[A-Z]\.\s*[A-Z]\.\s*[A-Z][A-Z\-]+(?:,|$|\s*&)'
        initials_surname_matches = re.findall(initials_surname_pattern, working_text)
        has_multiple_initials_surnames = len(initials_surname_matches) >= 2

        # Count commas in name - if many commas, likely a set
        comma_count = working_text.count(',')
        has_many_commas = comma_count >= 3

        # Check for names with associated numbers (e.g., "I. E. Santo 410, M. F. CASTILHORI 444")
        # Pattern: word/initial + space + digits + comma/separator + capital letter
        has_numbers_between_names = bool(re.search(r'[A-Za-z]+\s+\d+[,;\s]+[A-Z]\.?', working_text))

        # Check for keywords that indicate a group (ALUNOS, etc.)
        group_keywords_in_list = bool(re.search(r',\s*(ALUNOS|EQUIPE|GRUPO)', working_text, re.IGNORECASE))

        # Check for pattern: "Name & Name" or "Name, Name & Name"
        ampersand_with_names = bool(re.search(r'[A-Z][a-z]+,\s*[A-Z]\.\s*[A-Z]?\.*\s*&', working_text))

        # Check for multiple short initials/names separated by comma (e.g., "Y. Pires, C. GOMES, E. ADAIS")
        multiple_short_names = len(re.findall(r'[A-Z]\.\s*[A-Z][a-z]+', working_text)) >= 2

        if (has_separator and has_initials) or has_multiple_comma_names or has_multiple_initials_surnames or has_many_commas or has_numbers_between_names or group_keywords_in_list or ampersand_with_names or multiple_short_names:
            patterns_matched.extend(["multiple_names", "separator_detected"])
            return ClassificationOutput(
                original_text=text,
                sanitized_text=working_text,
                category=ClassificationCategory.CONJUNTO_PESSOAS,
                confidence=0.82,
                patterns_matched=patterns_matched,
                should_atomize=True
            )

        # 4. Pessoa (single name pattern)
        surname_pattern = r'^[A-ZÀ-Ú][a-zà-ú]+(?:-[A-ZÀ-Ú][a-zà-ú]+)?,\s*[A-ZÀ-Ú]\.(?:[A-ZÀ-Ú]\.)*'
        if re.match(surname_pattern, working_text):
            patterns_matched.append("surname_initials_format")
            return ClassificationOutput(
                original_text=text,
                sanitized_text=working_text,
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
                sanitized_text=working_text,
                category=ClassificationCategory.PESSOA,
                confidence=0.65,
                patterns_matched=patterns_matched,
                should_atomize=False
            )

        # Discard generic single names (first name or last name only)
        # Pattern: single word, no initials, title case or all caps
        # BUT: Allow single surnames if they have reasonable length (>3 chars) and title case
        if ' ' not in working_text and ',' not in working_text and '.' not in working_text:
            # Check if it's a potential surname (Title case, length > 3)
            # Examples to KEEP: "Cabrera", "Fabris", "Pabst", "Santos"
            # Examples to DISCARD: "A", "Bo", "Sol"
            if len(working_text) <= 3 or working_text.isupper() or working_text.islower():
                patterns_matched.append("generic_single_name")
                return ClassificationOutput(
                    original_text=text,
                    sanitized_text=working_text,
                    category=ClassificationCategory.NAO_DETERMINADO,
                    confidence=0.0,  # Signal to discard
                    patterns_matched=patterns_matched,
                    should_atomize=False
                )
            # If it passes the filter, treat as low-confidence person name
            patterns_matched.append("single_surname_only")
            return ClassificationOutput(
                original_text=text,
                sanitized_text=working_text,
                category=ClassificationCategory.PESSOA,
                confidence=0.55,  # Very low confidence for NER fallback
                patterns_matched=patterns_matched,
                should_atomize=False
            )

        # 5. Grupo de Pessoas (generic group terms)
        grupo_keywords = ["pesquisas", "grupo", "equipe", "time", "laboratório", "lab", "turma", "bioveg"]
        if any(kw in working_text.lower() for kw in grupo_keywords):
            patterns_matched.append("group_keyword")
            return ClassificationOutput(
                original_text=text,
                sanitized_text=working_text,
                category=ClassificationCategory.GRUPO_PESSOAS,
                confidence=0.75,
                patterns_matched=patterns_matched,
                should_atomize=False
            )

        # Default: Low confidence - use NER fallback
        result = ClassificationOutput(
            original_text=text,
            sanitized_text=working_text,
            category=ClassificationCategory.PESSOA,
            confidence=0.60,
            patterns_matched=["default_fallback"],
            should_atomize=False
        )

        # Always run NER when enabled (new requirement: 100% coverage) to refine category
        if self.use_ner_fallback:
            result = self._apply_ner_fallback(working_text, result)

        return result

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------
    def _sanitize_trailing_codes(self, text: str) -> tuple[str, bool]:
        """Remove trailing numeric/parenthetical specimen codes from the end of the string.

        Examples:
            "V.C. Vilela (67)" -> "V.C. Vilela"
            "M. Emmerich 1007" -> "M. Emmerich"
            "E. Santos 1092A" -> "E. Santos"

        We only remove AT THE END to avoid disturbing patterns that separate multiple names
        (e.g., "I. E. Santo 410, M. F. CASTILHORI 444") – those internal numbers help
        detect ConjuntoPessoas.
        """
        original = text
        # Remove parenthetical numeric codes at end
        text = re.sub(r"\s*\(\d+[A-Za-z]?\)\s*$", "", text)
        # Remove trailing standalone numeric token (optionally followed by single letter)
        text = re.sub(r"[\s,;-]*\b\d+[A-Za-z]?\b\s*$", "", text)
        sanitized = text.strip(" ,;-")
        return sanitized, sanitized != original

    def _apply_ner_fallback(
        self,
        text: str,
        original_result: ClassificationOutput
    ) -> ClassificationOutput:
        """
        Apply NER fallback to improve low-confidence classification
        AND extract only the person name portion from the text

        Args:
            text: Sanitized text (already has trailing numbers removed)
            original_result: Classification result with confidence < 0.85

        Returns:
            Updated ClassificationOutput with improved confidence or marked for discard
        """
        # Lazy load NER model (only on first use)
        if self.ner_fallback is None:
            self.ner_fallback = NERFallback(device=self.ner_device, model_key=self.ner_model)

        # First, extract only the person name portion if this is classified as PESSOA
        extracted_text = text
        if original_result.category == ClassificationCategory.PESSOA:
            extracted_text = self.ner_fallback.extract_person_name(text)

        # Run NER for classification
        ner_output = self.ner_fallback.classify_with_ner(
            extracted_text,
            original_result.confidence
        )

        self.ner_fallback_count += 1

        # Check if should discard
        if ner_output.should_discard or ner_output.improved_confidence == 0.0:
            patterns = original_result.patterns_matched.copy()
            patterns.append("ner_discard")
            return ClassificationOutput(
                original_text=original_result.original_text,
                sanitized_text=extracted_text,  # Use extracted text (person name only)
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
            original_text=original_result.original_text,
            sanitized_text=extracted_text,  # Use extracted text (person name only)
            category=category,
            confidence=ner_output.improved_confidence,
            patterns_matched=patterns,
            should_atomize=(category == ClassificationCategory.CONJUNTO_PESSOAS)
        )
