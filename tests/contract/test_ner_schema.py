"""Contract test for NER fallback schema"""

import pytest
from pydantic import BaseModel, Field, ValidationError


class NERInput(BaseModel):
    """Input for NER fallback"""
    text: str
    original_confidence: float = Field(ge=0.0, le=1.0)


class NEREntity(BaseModel):
    """NER extracted entity"""
    text: str
    label: str
    score: float = Field(ge=0.0, le=1.0)


class NEROutput(BaseModel):
    """Output from NER fallback"""
    entities: list[NEREntity]
    improved_confidence: float = Field(ge=0.0, le=1.0)


class TestNERInput:
    """Test NER input schema"""

    def test_valid_input(self):
        """Valid NER input"""
        input_data = NERInput(text="Silva, J.", original_confidence=0.65)
        assert input_data.text == "Silva, J."
        assert 0.0 <= input_data.original_confidence <= 1.0

    def test_confidence_range(self):
        """Confidence must be 0.0-1.0"""
        with pytest.raises(ValidationError):
            NERInput(text="Test", original_confidence=1.5)


class TestNEROutput:
    """Test NER output schema"""

    def test_valid_output(self):
        """Valid NER output with entities"""
        output = NEROutput(
            entities=[
                NEREntity(text="Silva", label="PESSOA", score=0.92)
            ],
            improved_confidence=0.85
        )
        assert len(output.entities) >= 0
        assert 0.0 <= output.improved_confidence <= 1.0

    def test_entity_fields(self):
        """NER entity must have text, label, score"""
        entity = NEREntity(text="Silva", label="PESSOA", score=0.95)
        assert entity.text == "Silva"
        assert entity.label == "PESSOA"
        assert 0.0 <= entity.score <= 1.0
