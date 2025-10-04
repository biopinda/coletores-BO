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
            original_confidence: Original classification confidence (should be < 0.70)

        Returns:
            NEROutput with extracted entities and improved confidence
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

        # Calculate improved confidence
        improved_confidence = self._calculate_improved_confidence(
            original_confidence,
            entities,
            has_person
        )

        return NEROutput(
            entities=entities,
            improved_confidence=improved_confidence,
            original_text=text,
            has_person=has_person
        )

    def _calculate_improved_confidence(
        self,
        original_confidence: float,
        entities: List[NEREntity],
        has_person: bool
    ) -> float:
        """
        Calculate improved confidence based on NER results

        Confidence boost logic:
        - If PESSOA entity found with high score (>0.85): +0.15 boost
        - If PESSOA entity found with medium score (>0.70): +0.10 boost
        - If PESSOA entity found with low score: +0.05 boost
        - If ORGANIZATION found: +0.05 boost
        - Maximum confidence: 0.95 (leave room for uncertainty)
        """
        confidence = original_confidence

        if not entities:
            # No entities found, slight penalty
            return max(confidence - 0.05, 0.65)

        # Find highest scoring PESSOA entity
        person_entities = [
            e for e in entities
            if e.label in ['PESSOA', 'PER', 'PERSON']
        ]

        if person_entities:
            max_person_score = max(e.score for e in person_entities)

            if max_person_score > 0.85:
                confidence += 0.15
            elif max_person_score > 0.70:
                confidence += 0.10
            else:
                confidence += 0.05

        # Check for organization entities
        org_entities = [
            e for e in entities
            if e.label in ['ORGANIZACAO', 'ORG', 'ORGANIZATION']
        ]

        if org_entities:
            confidence += 0.05

        # Cap at 0.95
        return min(confidence, 0.95)

    def should_use_fallback(self, confidence: float) -> bool:
        """
        Determine if NER fallback should be used

        Args:
            confidence: Original classification confidence

        Returns:
            True if confidence < 0.70 (threshold for NER fallback)
        """
        return confidence < 0.70
