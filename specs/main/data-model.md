# Data Model: Sistema de Identificação e Canonicalização de Coletores

## Entity Relationship Overview

```
MongoDBRecord (source)
    ↓
ClassificationResult
    ↓
AtomizedName[] (if conjunto_pessoas)
    ↓
NormalizedName
    ↓
CanonicalEntity ←→ NameVariation[]
```

---

## Core Entities

### 1. MongoDBRecord (Source Data)
**Purpose**: Input record from MongoDB collection

**Attributes**:
- `_id`: ObjectId - MongoDB document ID
- `kingdom`: str - Must equal "Plantae" (filter criteria)
- `collector_field`: str - Raw collector string to process
- `[other_fields]`: Any - Additional metadata (not processed)

**Validation Rules**:
- kingdom MUST equal "Plantae"
- collector_field MUST exist and be non-empty string

**State**: Immutable (read-only source data)

---

### 2. ClassificationResult
**Purpose**: Result of Stage 1 classification analysis

**Attributes**:
- `original_text`: str - Raw input string
- `category`: Enum[Pessoa, ConjuntoPessoas, GrupoPessoas, Empresa, NaoDeterminado]
- `confidence`: float - Range [0.0, 1.0]
- `patterns_matched`: List[str] - Which patterns triggered classification
- `should_atomize`: bool - True if category == ConjuntoPessoas

**Validation Rules**:
- confidence MUST be >= 0.70 (threshold from spec)
- If confidence < 0.70: flag for manual review
- category MUST be one of 5 valid enum values

**Relationships**:
- 1 MongoDBRecord → 1 ClassificationResult
- If should_atomize == True → generates AtomizedName[]

---

### 3. AtomizedName
**Purpose**: Individual name extracted from conjunto_pessoas

**Attributes**:
- `text`: str - Individual name string
- `original_formatting`: str - Preserved original format
- `source_text`: str - Original conjunto_pessoas string
- `position`: int - Order in original string (0-indexed)
- `separator_used`: Enum[Semicolon, Ampersand, EtAl, None]

**Validation Rules**:
- text MUST be non-empty
- original_formatting preserved for display
- position indicates extraction order

**Relationships**:
- 1 ClassificationResult → 0..N AtomizedName (0 if not conjunto_pessoas)
- Each AtomizedName → 1 NormalizedName

---

### 4. NormalizedName
**Purpose**: Standardized version of name for comparison

**Attributes**:
- `original`: str - Original name string
- `normalized`: str - Uppercase, standardized punctuation, trimmed spaces
- `normalization_rules_applied`: List[str] - ["remove_spaces", "uppercase", "standardize_punctuation"]

**Validation Rules**:
- normalized MUST be uppercase
- Spaces collapsed to single space
- Punctuation standardized (comma/period followed by space)

**Transformation Example**:
```
"  Silva,J.C. " → "SILVA, J.C."
"R.C.  Forzza" → "R.C. FORZZA"
```

**Relationships**:
- 1 AtomizedName → 1 NormalizedName
- 1 NormalizedName → 0..1 CanonicalEntity (via canonicalization)

---

### 5. CanonicalEntity
**Purpose**: Unique collector entity with grouped variations

**Attributes**:
- `id`: int - Primary key (auto-increment)
- `canonical_name`: str - Standardized "Sobrenome, Iniciais" format
- `entity_type`: Enum[Pessoa, GrupoPessoas, Empresa, NaoDeterminado]
- `classification_confidence`: float - Original classification confidence
- `grouping_confidence`: float - Confidence of variation grouping (≥0.70)
- `variations`: List[NameVariation] - All identified variations
- `created_at`: datetime
- `updated_at`: datetime

**Validation Rules**:
- canonical_name follows "Sobrenome, Iniciais" format for Pessoa type
- grouping_confidence MUST be ≥ 0.70
- variations list MUST contain at least 1 entry
- entity_type matches original classification category

**Uniqueness**:
- canonical_name is unique per entity_type (same name can exist as Pessoa and Empresa)

**Relationships**:
- 1 CanonicalEntity → 1..N NameVariation
- Updated dynamically during processing (not immutable)

---

### 6. NameVariation
**Purpose**: Specific representation of a canonical entity

**Attributes**:
- `variation_text`: str - Exact string as it appears in source data
- `occurrence_count`: int - Number of times seen in dataset
- `association_confidence`: float - Confidence this belongs to canonical entity [0.0-1.0]
- `first_seen`: datetime
- `last_seen`: datetime

**Validation Rules**:
- occurrence_count MUST be >= 1
- association_confidence MUST be >= 0.70 (spec threshold)
- variation_text is unique within a CanonicalEntity

**Relationships**:
- N NameVariation → 1 CanonicalEntity (embedded in JSON array)

**Update Logic**:
- When same variation_text found: increment occurrence_count, update last_seen
- New variation: append to CanonicalEntity.variations array

---

## Data Flow & State Transitions

### Pipeline Stage Flow

```
[MongoDB Input]
    ↓ (read kingdom=="Plantae")
[ClassificationResult] (NEW: classified)
    ↓ (if conjunto_pessoas)
[AtomizedName[]] (NEW: atomized) ←┐
    ↓                              │ (else: single name)
[NormalizedName] (NEW: normalized) ┘
    ↓ (similarity matching)
[Find/Create CanonicalEntity]
    ↓
[Add/Update NameVariation] (UPSERT)
    ↓
[Persist to Local DB]
```

### State Transitions for CanonicalEntity

1. **NEW**: Created when no existing entity matches (similarity < threshold)
2. **UPDATED**: Existing entity found, variation added/updated
3. **FINAL**: Processing complete, ready for CSV export

---

## Storage Schema (DuckDB/SQLite)

### Table: canonical_entities

```sql
CREATE TABLE canonical_entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_name TEXT NOT NULL,
    entity_type TEXT NOT NULL CHECK(entity_type IN ('Pessoa', 'GrupoPessoas', 'Empresa', 'NaoDeterminado')),
    classification_confidence REAL NOT NULL CHECK(classification_confidence >= 0.70 AND classification_confidence <= 1.0),
    grouping_confidence REAL NOT NULL CHECK(grouping_confidence >= 0.70 AND grouping_confidence <= 1.0),
    variations JSON NOT NULL, -- Array of {variation_text, occurrence_count, association_confidence, first_seen, last_seen}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX idx_canonical_name_type ON canonical_entities(canonical_name, entity_type);
CREATE INDEX idx_entity_type ON canonical_entities(entity_type);
CREATE INDEX idx_updated_at ON canonical_entities(updated_at);
```

### JSON Structure for `variations` field:

```json
[
  {
    "variation_text": "Forzza, R.C.",
    "occurrence_count": 1523,
    "association_confidence": 0.95,
    "first_seen": "2025-10-03T10:15:00Z",
    "last_seen": "2025-10-03T14:30:00Z"
  },
  {
    "variation_text": "R.C. Forzza",
    "occurrence_count": 847,
    "association_confidence": 0.88,
    "first_seen": "2025-10-03T10:20:00Z",
    "last_seen": "2025-10-03T15:00:00Z"
  }
]
```

---

## Validation & Constraints Summary

### Global Constraints
- **Confidence Threshold**: All confidence scores (classification, grouping, association) MUST be ≥ 0.70
- **Canonical Format**: Pessoa entities MUST follow "Sobrenome, Iniciais" format
- **Case Normalization**: All normalized names MUST be uppercase for comparison

### Data Quality Rules
1. No empty strings in any name field
2. Occurrence counts always >= 1
3. Variations array never empty for CanonicalEntity
4. Timestamps always populated (created_at, updated_at, first_seen, last_seen)

### Performance Constraints
- Indexed lookups on canonical_name + entity_type (O(log n))
- JSON variations stored inline (no JOIN overhead)
- Batch updates to minimize DB writes during 6-hour processing

---

## Pydantic Models (Type-Safe Implementation)

### Python Representation

```python
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from datetime import datetime
from typing import List

class EntityType(str, Enum):
    PESSOA = "Pessoa"
    GRUPO_PESSOAS = "GrupoPessoas"
    EMPRESA = "Empresa"
    NAO_DETERMINADO = "NaoDeterminado"

class ClassificationCategory(str, Enum):
    PESSOA = "Pessoa"
    CONJUNTO_PESSOAS = "ConjuntoPessoas"
    GRUPO_PESSOAS = "GrupoPessoas"
    EMPRESA = "Empresa"
    NAO_DETERMINADO = "NaoDeterminado"

class ClassificationResult(BaseModel):
    original_text: str
    category: ClassificationCategory
    confidence: float = Field(ge=0.0, le=1.0)
    patterns_matched: List[str]
    should_atomize: bool

    @field_validator('confidence')
    def check_threshold(cls, v):
        if v < 0.70:
            raise ValueError('Confidence below threshold (0.70)')
        return v

class NormalizedName(BaseModel):
    original: str
    normalized: str
    normalization_rules_applied: List[str]

    @field_validator('normalized')
    def must_be_uppercase(cls, v):
        if v != v.upper():
            raise ValueError('Normalized name must be uppercase')
        return v

class NameVariation(BaseModel):
    variation_text: str
    occurrence_count: int = Field(ge=1)
    association_confidence: float = Field(ge=0.70, le=1.0)
    first_seen: datetime
    last_seen: datetime

class CanonicalEntity(BaseModel):
    id: int | None = None
    canonical_name: str
    entity_type: EntityType
    classification_confidence: float = Field(ge=0.70, le=1.0)
    grouping_confidence: float = Field(ge=0.70, le=1.0)
    variations: List[NameVariation] = Field(min_length=1)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
```

---

## CSV Export Schema

### Output Format (canonical_report.csv)

| canonical_name | entity_type | variations | occurrence_counts |
|---------------|-------------|-----------|-------------------|
| Forzza, R.C. | Pessoa | "Forzza, R.C.;R.C. Forzza;Rafaela C. Forzza" | "1523;847;234" |
| Silva, J. | Pessoa | "Silva, J.;J. Silva" | "2891;1205" |
| EMBRAPA | Empresa | "EMBRAPA" | "45" |

**Column Specifications**:

1. `canonical_name`: str - Canonical entity name
2. `entity_type`: str - Entity classification type (Pessoa/GrupoPessoas/Empresa/NaoDeterminado)
3. `variations`: str - Semicolon-separated list of variation texts
4. `occurrence_counts`: str - Semicolon-separated counts (aligned with variations)

**Format Details**:

- **Separator**: TAB (tabulation character)
- **Encoding**: UTF-8
- **Confidence scores**: NOT included in CSV (per spec FR-025)

---

## Summary

- ✅ All entities from spec mapped to structured models
- ✅ Validation rules enforce confidence thresholds (≥0.70)
- ✅ Relationships clearly defined (ClassificationResult → AtomizedName → NormalizedName → CanonicalEntity)
- ✅ Storage schema supports dynamic updates with JSON variations
- ✅ Pydantic models provide type safety and runtime validation
- ✅ CSV export format matches spec requirements (4 columns, no confidence scores)

**Ready for**: Contract generation and test scenario creation.
