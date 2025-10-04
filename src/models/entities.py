"""Data models and entities - Re-export from contracts for consistency"""

# Import all models from contracts to avoid duplication
from .contracts import (
    EntityType,
    ClassificationCategory,
    CanonicalVariation as NameVariation,  # Alias for backward compatibility
    CanonicalEntity,
    ClassificationInput,
    ClassificationOutput,
    AtomizationInput,
    AtomizationOutput,
    AtomizedName,
    NormalizationInput,
    NormalizationOutput,
    CanonicalizationInput,
    CanonicalizationOutput,
)

# Re-export for convenience
__all__ = [
    'EntityType',
    'ClassificationCategory',
    'NameVariation',
    'CanonicalEntity',
    'ClassificationInput',
    'ClassificationOutput',
    'AtomizationInput',
    'AtomizationOutput',
    'AtomizedName',
    'NormalizationInput',
    'NormalizationOutput',
    'CanonicalizationInput',
    'CanonicalizationOutput',
]
