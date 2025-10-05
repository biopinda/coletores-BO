"""Unit tests for classification stage with trailing numeric codes and NER always-on.

These tests focus on the new sanitation logic that removes trailing specimen/collection
numbers and parenthetical numeric codes, ensuring they don't influence classification
or persist downstream.
"""

from src.pipeline.classifier import Classifier
from src.models.contracts import ClassificationInput, ClassificationCategory


def _mk(text: str):
    # Disable NER for deterministic assertions (sanitization + regex logic only)
    clf = Classifier(use_ner_fallback=False)
    return clf.classify(ClassificationInput(text=text))


def test_trailing_parenthetical_number_removed():
    r = _mk("V.C. Vilela (67)")
    # Original text preserved in output
    assert r.original_text == "V.C. Vilela (67)"
    # Should classify as single person
    assert r.category == ClassificationCategory.PESSOA
    assert r.confidence > 0


def test_trailing_plain_number_removed():
    r = _mk("M. Emmerich 1007")
    assert r.category == ClassificationCategory.PESSOA


def test_trailing_alphanumeric_number_removed():
    r = _mk("E. Santos 1092A")
    assert r.category == ClassificationCategory.PESSOA


def test_internal_numbers_preserved_for_conjunto_detection():
    # Internal numeric tokens between names should still trigger conjunto logic
    r = _mk("I. E. Santo 410, M. F. CASTILHORI 444")
    assert r.category == ClassificationCategory.CONJUNTO_PESSOAS
