"""NER fallback for low-confidence classification cases"""

from typing import List, Optional
from dataclasses import dataclass
import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline


@dataclass
class NEREntity:
    """Named entity extracted by NER model"""
    text: str
    label: str
    score: float
    start: int
    end: int


@dataclass
class NEROutput:
    """Output from NER fallback"""
    entities: List[NEREntity]
    improved_confidence: float
    original_text: str
    has_person: bool
    should_discard: bool  # True if string should be discarded


class NERFallback:
    """NER-based fallback for low-confidence classification using Portuguese BERT"""

    # Model: Portuguese BERT fine-tuned on LeNER-Br (Brazilian legal NER dataset)
    MODEL_NAME = "pierreguillou/bert-base-cased-pt-lenerbr"

    def __init__(self, device: Optional[str] = None):
        """
        Initialize NER model

        Args:
            device: 'cuda' for GPU, 'cpu' for CPU, or None for auto-detect
        """
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.tokenizer = None
        self.ner_pipeline = None

        # Lazy load - only load when first used
        self._load_model()

    def _load_model(self) -> None:
        """Load NER model and tokenizer (cached after first load)"""
        if self.ner_pipeline is not None:
            return

        print(f"Loading NER model: {self.MODEL_NAME} on {self.device}...")

        self.tokenizer = AutoTokenizer.from_pretrained(self.MODEL_NAME)
        self.model = AutoModelForTokenClassification.from_pretrained(self.MODEL_NAME)

        # Move model to GPU if available
        if self.device == 'cuda':
            self.model = self.model.to('cuda')

        # Create pipeline for easier inference
        self.ner_pipeline = pipeline(
            "ner",
            model=self.model,
            tokenizer=self.tokenizer,
            device=0 if self.device == 'cuda' else -1,  # 0 = first GPU, -1 = CPU
            aggregation_strategy="simple"  # Merge subword tokens
        )

        print(f"[OK] NER model loaded successfully on {self.device}")

    def classify_with_ner(self, text: str, original_confidence: float) -> NEROutput:
        """
        Use NER to improve classification for low-confidence cases

        Args:
            text: Input text to classify
            original_confidence: Original classification confidence

        Returns:
            NEROutput with extracted entities, improved confidence, and discard flag
        """
        # Ensure model is loaded
        self._load_model()

        # Run NER
        ner_results = self.ner_pipeline(text)

        # Convert to our entity format
        entities = []
        has_person = False

        for result in ner_results:
            entity = NEREntity(
                text=result['word'],
                label=result['entity_group'],
                score=result['score'],
                start=result['start'],
                end=result['end']
            )
            entities.append(entity)

            # Check if we found a person entity
            if entity.label in ['PESSOA', 'PER', 'PERSON']:
                has_person = True

        # Determine if we should discard this string
        should_discard = self._should_discard(text, entities, has_person)

        # Calculate improved confidence
        improved_confidence = self._calculate_improved_confidence(
            original_confidence,
            entities,
            has_person,
            should_discard
        )

        return NEROutput(
            entities=entities,
            improved_confidence=improved_confidence,
            original_text=text,
            has_person=has_person,
            should_discard=should_discard
        )

    def _should_discard(self, text: str, entities: List[NEREntity], has_person: bool) -> bool:
        """
        Determine if a string should be discarded

        Discard criteria:
        - No recognized entities found
        - All entities have very low confidence (<0.50)
        - Text is too short (<3 characters) and no entities
        - Text has suspicious patterns (mostly numbers, special chars)
        """
        import re

        # Too short without clear entity
        if len(text.strip()) < 3 and not entities:
            return True

        # No entities found at all
        if not entities:
            # Check if text looks like garbage (mostly non-alphabetic)
            alpha_ratio = sum(c.isalpha() for c in text) / max(len(text), 1)
            if alpha_ratio < 0.5:
                return True
            # If it's very short and no entities, likely not useful
            if len(text.strip()) < 5:
                return True

        # All entities have very low confidence
        if entities:
            max_score = max(e.score for e in entities)
            if max_score < 0.50:
                return True

        return False

    def _calculate_improved_confidence(
        self,
        original_confidence: float,
        entities: List[NEREntity],
        has_person: bool,
        should_discard: bool
    ) -> float:
        """
        Calculate improved confidence based on NER results

        Confidence logic:
        - If should_discard: return 0.0 (will be filtered out)
        - If PESSOA entity found with high score (>0.85): boost to 0.85-0.90
        - If PESSOA entity found with medium score (>0.70): boost to 0.75-0.80
        - If PESSOA entity found with low score (>0.50): boost to 0.70-0.75
        - If ORGANIZATION found: boost accordingly
        - If no clear entities: reduce confidence to 0.65-0.70
        - Maximum confidence: 0.90 (more conservative)
        """
        if should_discard:
            return 0.0  # Signal to discard

        confidence = original_confidence

        if not entities:
            # No entities found, reduce confidence
            return max(confidence - 0.10, 0.65)

        # Find highest scoring PESSOA entity
        person_entities = [
            e for e in entities
            if e.label in ['PESSOA', 'PER', 'PERSON']
        ]

        if person_entities:
            max_person_score = max(e.score for e in person_entities)

            if max_person_score > 0.85:
                confidence = 0.85
            elif max_person_score > 0.70:
                confidence = 0.75
            elif max_person_score > 0.50:
                confidence = 0.70
            else:
                confidence = 0.65

        # Check for organization entities
        org_entities = [
            e for e in entities
            if e.label in ['ORGANIZACAO', 'ORG', 'ORGANIZATION']
        ]

        if org_entities and not person_entities:
            max_org_score = max(e.score for e in org_entities)
            if max_org_score > 0.85:
                confidence = 0.85
            elif max_org_score > 0.70:
                confidence = 0.75
            else:
                confidence = 0.70

        # Cap at 0.90 (more conservative)
        return min(confidence, 0.90)

    def should_use_fallback(self, confidence: float) -> bool:
        """
        Determine if NER fallback should be used

        Args:
            confidence: Original classification confidence

        Returns:
            True if confidence < 0.85 (threshold for NER fallback - more generous)
        """
        return confidence < 0.85
