"""Contract test for normalization schema"""

import pytest
from pydantic import ValidationError
from src.models.contracts import NormalizationInput, NormalizationOutput


class TestNormalizationInput:
    """Test NormalizationInput schema"""

    def test_valid_input(self):
        """Valid input: original_name with min_length=1"""
        input_data = NormalizationInput(original_name="  Silva,J.C. ")
        assert input_data.original_name == "  Silva,J.C. "

    def test_empty_string_rejected(self):
        """Invalid input: empty string violates min_length=1"""
        with pytest.raises(ValidationError):
            NormalizationInput(original_name="")


class TestNormalizationOutput:
    """Test NormalizationOutput schema"""

    def test_valid_output(self):
        """Valid output: normalized is uppercase"""
        output = NormalizationOutput(
            original="  Silva,J.C. ",
            normalized="SILVA, J.C.",
            rules_applied=["remove_extra_spaces", "standardize_punctuation", "uppercase"]
        )
        assert output.normalized == "SILVA, J.C."
        assert output.normalized.isupper()

    def test_rules_applied_list(self):
        """rules_applied must be a list of strings"""
        output = NormalizationOutput(
            original="Test",
            normalized="TEST",
            rules_applied=["uppercase", "trim"]
        )
        assert isinstance(output.rules_applied, list)
        assert len(output.rules_applied) == 2
