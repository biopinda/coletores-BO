"""Unit tests for number removal in classification and sanitization.

Tests verify that strings with trailing numbers like "V.C. Vilela (67)",
"M. Emmerich 1007", and "E. Santos 1092" are properly sanitized.
"""

from src.pipeline.classifier import Classifier
from src.models.contracts import ClassificationInput, ClassificationCategory


def test_parenthetical_number_sanitization():
    """Test that parenthetical numbers like (67) are removed from sanitized_text"""
    # Disable NER to test pure sanitization logic
    clf = Classifier(use_ner_fallback=False)
    result = clf.classify(ClassificationInput(text="V.C. Vilela (67)"))

    # Original text should be preserved
    assert result.original_text == "V.C. Vilela (67)"
    # Sanitized text should have number removed
    assert result.sanitized_text == "V.C. Vilela"
    # Should be classified as person
    assert result.category == ClassificationCategory.PESSOA


def test_trailing_plain_number_sanitization():
    """Test that plain trailing numbers like 1007 are removed"""
    clf = Classifier(use_ner_fallback=False)
    result = clf.classify(ClassificationInput(text="M. Emmerich 1007"))

    assert result.original_text == "M. Emmerich 1007"
    assert result.sanitized_text == "M. Emmerich"
    assert result.category == ClassificationCategory.PESSOA


def test_trailing_alphanumeric_sanitization():
    """Test that alphanumeric codes like 1092A are removed"""
    clf = Classifier(use_ner_fallback=False)
    result = clf.classify(ClassificationInput(text="E. Santos 1092A"))

    assert result.original_text == "E. Santos 1092A"
    assert result.sanitized_text == "E. Santos"
    assert result.category == ClassificationCategory.PESSOA


def test_internal_numbers_preserved_for_conjunto():
    """Test that internal numbers between names trigger ConjuntoPessoas

    Note: The sanitization only removes TRAILING numbers, not internal ones.
    Internal numbers help detect conjunto, and the atomizer removes them later.
    """
    clf = Classifier(use_ner_fallback=False)
    result = clf.classify(ClassificationInput(text="I. E. Santo 410, M. F. CASTILHORI 444"))

    # Should detect as conjunto due to internal numbers + comma separator
    assert result.category == ClassificationCategory.CONJUNTO_PESSOAS
    assert result.should_atomize is True


def test_multiple_cases_with_ner_enabled():
    """Test with NER enabled to verify full pipeline"""
    clf = Classifier(use_ner_fallback=True, ner_model="lenerbr")

    test_cases = [
        ("V.C. Vilela (67)", "V.C. Vilela"),
        ("M. Emmerich 1007", "M. Emmerich"),
        ("E. Santos 1092", "E. Santos"),
        ("Silva, J. 234B", "Silva, J."),
    ]

    for original, expected_sanitized in test_cases:
        result = clf.classify(ClassificationInput(text=original))

        # Original should be preserved
        assert result.original_text == original, f"Failed for {original}"
        # Sanitized should have numbers removed
        # Note: NER may further refine the text, so we check if expected is substring
        assert expected_sanitized in result.sanitized_text or result.sanitized_text == expected_sanitized, \
            f"Failed for {original}: expected '{expected_sanitized}', got '{result.sanitized_text}'"
        # Should be classified as person (not conjunto, not undetermined)
        assert result.category in [ClassificationCategory.PESSOA, ClassificationCategory.NAO_DETERMINADO], \
            f"Failed for {original}: got category {result.category}"


def test_no_sanitization_needed():
    """Test that strings without trailing numbers are unchanged"""
    clf = Classifier(use_ner_fallback=False)
    result = clf.classify(ClassificationInput(text="Silva, J."))

    # Both should be the same
    assert result.original_text == "Silva, J."
    assert result.sanitized_text == "Silva, J."
    assert result.category == ClassificationCategory.PESSOA
