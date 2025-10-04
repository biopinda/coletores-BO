"""Contract test for atomization schema"""

import pytest
from pydantic import ValidationError
from src.models.contracts import (
    AtomizationInput,
    AtomizationOutput,
    AtomizedName,
    ClassificationCategory,
    SeparatorType
)


class TestAtomizationInput:
    """Test AtomizationInput schema"""

    def test_valid_input(self):
        """Valid input: text + category"""
        input_data = AtomizationInput(
            text="Silva, J. & R.C. Forzza",
            category=ClassificationCategory.CONJUNTO_PESSOAS
        )
        assert input_data.text == "Silva, J. & R.C. Forzza"
        assert input_data.category == ClassificationCategory.CONJUNTO_PESSOAS


class TestAtomizedName:
    """Test AtomizedName schema"""

    def test_valid_atomized_name(self):
        """Valid AtomizedName with all required fields"""
        name = AtomizedName(
            text="Silva, J.",
            original_formatting="Silva, J.",
            position=0,
            separator_used=SeparatorType.AMPERSAND
        )
        assert name.text == "Silva, J."
        assert name.position == 0

    def test_text_min_length(self):
        """text must have min_length=1"""
        with pytest.raises(ValidationError):
            AtomizedName(
                text="",
                original_formatting="",
                position=0,
                separator_used=SeparatorType.NONE
            )

    def test_position_non_negative(self):
        """position must be >= 0"""
        with pytest.raises(ValidationError):
            AtomizedName(
                text="Test",
                original_formatting="Test",
                position=-1,
                separator_used=SeparatorType.NONE
            )


class TestAtomizationOutput:
    """Test AtomizationOutput schema"""

    def test_empty_list_for_non_conjunto(self):
        """Empty atomized_names list for non-ConjuntoPessoas categories"""
        output = AtomizationOutput(
            original_text="Silva, J.",
            atomized_names=[]
        )
        assert output.atomized_names == []

    def test_atomized_names_list(self):
        """Valid list of AtomizedName objects"""
        output = AtomizationOutput(
            original_text="Silva, J. & R.C. Forzza",
            atomized_names=[
                AtomizedName(
                    text="Silva, J.",
                    original_formatting="Silva, J.",
                    position=0,
                    separator_used=SeparatorType.AMPERSAND
                ),
                AtomizedName(
                    text="R.C. Forzza",
                    original_formatting="R.C. Forzza",
                    position=1,
                    separator_used=SeparatorType.NONE
                )
            ]
        )
        assert len(output.atomized_names) == 2
        assert output.atomized_names[0].text == "Silva, J."
        assert output.atomized_names[1].text == "R.C. Forzza"
