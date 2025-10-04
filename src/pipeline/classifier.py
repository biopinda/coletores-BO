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
                confidence=0.95,
                patterns_matched=patterns_matched,
                should_atomize=False
            )
        
        # 3. Conjunto de Pessoas (separators + name patterns)
        conjunto_separators = [';', '&', 'et al.', ' e ', ' and ']
        has_separator = any(sep in text for sep in conjunto_separators)
        has_initials = bool(re.search(r'\b[A-Z]\.\s*[A-Z]\.?', text))
        
        if has_separator and has_initials:
            patterns_matched.extend(["multiple_names", "separator_detected"])
            return ClassificationOutput(
                original_text=text,
                category=ClassificationCategory.CONJUNTO_PESSOAS,
                confidence=0.92,
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
                confidence=0.90,
                patterns_matched=patterns_matched,
                should_atomize=False
            )
        
        # Check for initials without strict surname format
        if has_initials and not has_separator:
            patterns_matched.append("single_name_with_initials")
            return ClassificationOutput(
                original_text=text,
                category=ClassificationCategory.PESSOA,
                confidence=0.75,
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
                confidence=0.80,
                patterns_matched=patterns_matched,
                should_atomize=False
            )
        
        # Default: Pessoa (conservative fallback) - but check if we need NER
        result = ClassificationOutput(
            original_text=text,
            category=ClassificationCategory.PESSOA,
            confidence=0.70,
            patterns_matched=["default_fallback"],
            should_atomize=False
        )

        # NER fallback for low-confidence cases
        if self.use_ner_fallback and result.confidence < 0.70:
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
            original_result: Classification result with confidence < 0.70

        Returns:
            Updated ClassificationOutput with improved confidence
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

        # Update category based on NER findings
        category = original_result.category
        patterns = original_result.patterns_matched.copy()
        patterns.append("ner_fallback")

        if ner_output.has_person:
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
            should_atomize=False
        )
