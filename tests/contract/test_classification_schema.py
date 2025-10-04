"""Contract test for classification schema"""

import pytest
from pydantic import ValidationError
from src.models.contracts import ClassificationInput, ClassificationOutput, ClassificationCategory


class TestClassificationInput:
    """Test ClassificationInput schema"""

    def test_valid_input(self):
        """Valid input: text with min_length=1"""
        input_data = ClassificationInput(text="Silva, J. & Forzza, R.C.")
        assert input_data.text == "Silva, J. & Forzza, R.C."

    def test_empty_string_rejected(self):
        """Invalid input: empty string violates min_length=1"""
        with pytest.raises(ValidationError):
            ClassificationInput(text="")


class TestClassificationOutput:
    """Test ClassificationOutput schema"""

    @pytest.mark.parametrize("category", [
        ClassificationCategory.PESSOA,
        ClassificationCategory.CONJUNTO_PESSOAS,
        ClassificationCategory.GRUPO_PESSOAS,
        ClassificationCategory.EMPRESA,
        ClassificationCategory.NAO_DETERMINADO,
    ])
    def test_valid_categories(self, category):
        """Valid output: category must be one of 5 enum values"""
        output = ClassificationOutput(
            original_text="Test",
            category=category,
            confidence=0.85,
            patterns_matched=["test_pattern"],
            should_atomize=(category == ClassificationCategory.CONJUNTO_PESSOAS)
        )
        assert output.category == category

    @pytest.mark.parametrize("confidence", [0.0, 0.5, 0.70, 0.85, 1.0])
    def test_valid_confidence_range(self, confidence):
        """Valid confidence: 0.0-1.0 range accepted"""
        output = ClassificationOutput(
            original_text="Test",
            category=ClassificationCategory.PESSOA,
            confidence=confidence,
            patterns_matched=["test"],
            should_atomize=False
        )
        assert output.confidence == confidence

    @pytest.mark.parametrize("invalid_confidence", [-0.1, 1.1, 2.0])
    def test_invalid_confidence_range(self, invalid_confidence):
        """Invalid confidence: outside 0.0-1.0 range rejected"""
        with pytest.raises(ValidationError):
            ClassificationOutput(
                original_text="Test",
                category=ClassificationCategory.PESSOA,
                confidence=invalid_confidence,
                patterns_matched=["test"],
                should_atomize=False
            )

    def test_should_atomize_flag(self):
        """should_atomize must be boolean"""
        output = ClassificationOutput(
            original_text="Test",
            category=ClassificationCategory.CONJUNTO_PESSOAS,
            confidence=0.90,
            patterns_matched=["multiple_names"],
            should_atomize=True
        )
        assert output.should_atomize is True
        assert isinstance(output.should_atomize, bool)
