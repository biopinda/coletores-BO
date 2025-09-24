# Data Model: Sistema de Canonicalização de Coletores Biológicos

**Phase**: Phase 1 - Design & Contracts
**Date**: 2025-09-24
**Dependencies**: research.md

## Overview

This data model defines the entities and relationships for the biological collector canonicalization system, based on the feature specifications and research findings. The model supports 6 classification types and similarity-based canonicalization of 11M+ specimen records.

## Core Entities

### 1. CollectorRecord
**Source specimen record containing collector information**

```python
@dataclass
class CollectorRecord:
    """Individual specimen record from MongoDB collection"""

    # Primary identifiers
    document_id: ObjectId                    # MongoDB _id
    recorded_by: str                         # Original recordedBy string
    kingdom: str                             # Biological kingdom (Plantae/Animalia)

    # Occurrence metadata
    occurrence_id: Optional[str]             # Specimen occurrence identifier
    collection_date: Optional[datetime]      # When specimen was collected
    dataset_name: Optional[str]              # Source dataset
    institution_code: Optional[str]          # Institution responsible

    # Processing metadata
    created_at: datetime                     # Record creation timestamp
    last_modified: datetime                  # Last modification timestamp
    processing_status: str = "pending"       # pending, processed, error, manual_review
    processing_errors: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate required fields and normalize data"""
        if not self.recorded_by or not self.recorded_by.strip():
            raise ValueError("recorded_by cannot be empty")
        if self.kingdom not in ["Plantae", "Animalia"]:
            raise ValueError(f"Invalid kingdom: {self.kingdom}")
```

### 2. ClassificationResult
**Entity type determination with confidence scoring**

```python
@dataclass
class ClassificationResult:
    """Result of collector string classification"""

    # Classification outcome
    entity_type: str                         # pessoa, conjunto_pessoas, grupo_pessoas,
                                            # empresa_instituicao, coletor_indeterminado,
                                            # representacao_insuficiente
    confidence_score: float                  # 0.0-1.0 confidence in classification
    reasoning: str                           # Human-readable explanation

    # Classification details
    detected_patterns: List[str]             # Regex patterns that matched
    separator_found: Optional[str]           # Separator used for multi-person detection
    institutional_indicators: List[str]      # Keywords suggesting institution

    # Metadata
    classifier_version: str                  # Version of classification algorithm
    classification_timestamp: datetime      # When classification occurred

    def requires_manual_review(self) -> bool:
        """Check if classification needs manual review"""
        return (self.confidence_score < 0.5 or
                self.entity_type in ["representacao_insuficiente", "coletor_indeterminado"])

    def is_canonicalizable(self) -> bool:
        """Check if result can participate in canonicalization"""
        return self.entity_type in ["pessoa", "conjunto_pessoas", "grupo_pessoas", "empresa_instituicao"]
```

### 3. CanonicalCollector
**Normalized collector identity with grouped variations**

```python
@dataclass
class CanonicalCollector:
    """Canonical form representing a unique collector identity"""

    # Identity
    canonical_id: str                        # Unique identifier (UUID)
    canonical_form: str                      # Chosen representative name
    entity_type: str                         # Classification type
    confidence_score: float                  # Overall confidence in canonicalization

    # Name components (for pessoa/conjunto_pessoas types)
    surname_normalized: Optional[str]        # Normalized surname
    initials: Optional[Set[str]]             # Set of initials
    full_names: Optional[Set[str]]           # Set of known full names

    # Phonetic keys
    phonetic_keys: Dict[str, str]           # soundex, metaphone, double_metaphone keys

    # Variations and statistics
    variations: List['CollectorVariation']   # All variations grouped under this canonical
    total_occurrences: int                   # Total specimens across all variations
    first_occurrence: datetime               # Earliest occurrence date
    last_occurrence: datetime                # Latest occurrence date

    # Kingdom specialization
    kingdom_statistics: Dict[str, 'KingdomStatistics']  # Plantae/Animalia breakdown

    # Metadata
    created_at: datetime
    last_updated: datetime
    manual_review_status: str = "none"       # none, pending, approved, rejected
    quality_flags: List[str] = field(default_factory=list)  # Potential issues

    def add_variation(self, variation: 'CollectorVariation'):
        """Add a new variation to this canonical collector"""
        self.variations.append(variation)
        self.total_occurrences += variation.frequency_count

        if variation.first_occurrence < self.first_occurrence:
            self.first_occurrence = variation.first_occurrence
        if variation.last_occurrence > self.last_occurrence:
            self.last_occurrence = variation.last_occurrence

        self.last_updated = datetime.now()

    def get_specialization_score(self) -> Dict[str, float]:
        """Calculate kingdom specialization percentages"""
        total = sum(stats.collection_count for stats in self.kingdom_statistics.values())
        if total == 0:
            return {}
        return {
            kingdom: stats.collection_count / total
            for kingdom, stats in self.kingdom_statistics.items()
        }
```

### 4. CollectorVariation
**Individual form of collector name with occurrence data**

```python
@dataclass
class CollectorVariation:
    """Specific variation of a collector name"""

    # Identity
    variation_id: str                        # Unique identifier
    original_text: str                       # Exact text from recordedBy field
    normalized_text: str                     # Cleaned and normalized version
    canonical_id: str                        # Parent canonical collector ID

    # Frequency data
    frequency_count: int                     # Number of occurrences
    first_occurrence: datetime               # First seen date
    last_occurrence: datetime                # Last seen date

    # Similarity metrics (to canonical form)
    similarity_scores: 'SimilarityScore'     # Detailed similarity breakdown

    # Source tracking
    source_records: List[ObjectId]           # MongoDB _ids of source records
    kingdom_distribution: Dict[str, int]     # Count by kingdom

    # Quality indicators
    quality_score: float                     # 0.0-1.0 quality assessment
    anomaly_flags: List[str] = field(default_factory=list)  # Detected anomalies

    def __post_init__(self):
        """Validate and normalize variation data"""
        if self.frequency_count < 1:
            raise ValueError("Frequency count must be positive")
        if not self.original_text.strip():
            raise ValueError("Original text cannot be empty")
```

### 5. SimilarityScore
**Detailed similarity metrics between collector names**

```python
@dataclass
class SimilarityScore:
    """Comprehensive similarity calculation breakdown"""

    # Overall score
    composite_score: float                   # Final weighted score (0.0-1.0)
    threshold_met: bool                      # Whether score exceeds grouping threshold

    # Component scores (as specified: 50%, 30%, 20%)
    surname_similarity: float                # Jaro-Winkler similarity of surnames
    surname_weight: float = 0.5             # Weight applied to surname component

    initial_compatibility: float             # Jaccard similarity of initial sets
    initial_weight: float = 0.3             # Weight applied to initial component

    phonetic_similarity: float               # Average of phonetic algorithm matches
    phonetic_weight: float = 0.2            # Weight applied to phonetic component

    # Detailed phonetic breakdown
    phonetic_details: Dict[str, bool] = field(default_factory=dict)  # soundex, metaphone, double_metaphone matches

    # Algorithm metadata
    algorithm_version: str                   # Version of similarity algorithm
    calculation_timestamp: datetime         # When score was calculated

    @classmethod
    def calculate(cls, name1: Dict, name2: Dict) -> 'SimilarityScore':
        """Calculate similarity score between two normalized names"""
        # Implementation based on research findings
        surname_sim = jaro_winkler_similarity(
            name1.get('surname_normalized', ''),
            name2.get('surname_normalized', '')
        )

        initial_compat = calculate_initial_compatibility(
            name1.get('initials', set()),
            name2.get('initials', set())
        )

        phonetic_sim = calculate_phonetic_similarity(
            name1.get('phonetic_keys', {}),
            name2.get('phonetic_keys', {})
        )

        composite = (0.5 * surname_sim) + (0.3 * initial_compat) + (0.2 * phonetic_sim)

        return cls(
            composite_score=composite,
            threshold_met=composite >= 0.85,  # From research
            surname_similarity=surname_sim,
            initial_compatibility=initial_compat,
            phonetic_similarity=phonetic_sim,
            algorithm_version="1.0",
            calculation_timestamp=datetime.now()
        )
```

### 6. KingdomStatistics
**Collector activity breakdown by biological kingdom**

```python
@dataclass
class KingdomStatistics:
    """Statistical breakdown of collector activity by kingdom"""

    # Basic counts
    kingdom: str                             # Plantae or Animalia
    collection_count: int                    # Number of specimens collected
    unique_taxa_count: int                   # Number of different taxa

    # Temporal distribution
    first_collection: datetime               # Earliest collection date
    last_collection: datetime                # Latest collection date
    active_years: int                        # Number of years with collections

    # Geographic distribution (if available)
    countries: Set[str] = field(default_factory=set)      # Countries where collected
    locations_count: int = 0                 # Number of unique collection locations

    # Specialization indicators
    specialization_score: float = 0.0       # 0.0-1.0 how specialized in this kingdom
    primary_families: List[str] = field(default_factory=list)  # Most collected families

    def calculate_specialization(self, total_collections: int):
        """Calculate how specialized collector is in this kingdom"""
        if total_collections == 0:
            self.specialization_score = 0.0
        else:
            self.specialization_score = self.collection_count / total_collections
```

## Supporting Data Structures

### ProcessingBatch
**Batch processing state for checkpoint recovery**

```python
@dataclass
class ProcessingBatch:
    """State information for batch processing operations"""

    batch_id: str                            # Unique batch identifier
    start_document_id: ObjectId              # First document in batch
    end_document_id: ObjectId                # Last document in batch
    batch_size: int                          # Number of records in batch

    # Processing status
    status: str                              # pending, processing, completed, error
    started_at: Optional[datetime]           # Processing start time
    completed_at: Optional[datetime]         # Processing completion time
    error_message: Optional[str]             # Error details if failed

    # Statistics
    records_processed: int = 0               # Successfully processed records
    records_skipped: int = 0                 # Skipped records
    records_failed: int = 0                  # Failed records

    # Results
    classifications_created: int = 0         # New classifications
    canonicals_created: int = 0              # New canonical collectors
    variations_added: int = 0                # New variations added
```

### CheckpointData
**Checkpoint state for recovery**

```python
@dataclass
class CheckpointData:
    """Checkpoint information for process recovery"""

    checkpoint_id: str                       # Unique checkpoint identifier
    checkpoint_type: str                     # macro, micro, batch
    process_type: str                        # canonicalization, validation, reporting

    # Progress information
    total_records: int                       # Total records to process
    processed_records: int                   # Records processed so far
    last_document_id: ObjectId               # Last processed document
    current_batch_number: int                # Current batch number

    # State information
    algorithm_state: bytes                   # Compressed algorithm state
    statistics_snapshot: Dict               # Current processing statistics

    # Metadata
    created_at: datetime
    process_version: str                     # Version of processing algorithm
    configuration_hash: str                  # Hash of current configuration
```

## Entity Relationships

### Primary Relationships

1. **CollectorRecord → ClassificationResult**: 1:1
   - Each record gets one classification result

2. **ClassificationResult → CanonicalCollector**: M:1 (if canonicalizable)
   - Multiple classifications can map to same canonical

3. **CanonicalCollector → CollectorVariation**: 1:M
   - Each canonical has multiple variations

4. **CollectorVariation → CollectorRecord**: M:M
   - Variations reference multiple source records

5. **CanonicalCollector → KingdomStatistics**: 1:M
   - Each canonical has statistics per kingdom

## Data Validation Rules

### Business Rules
1. **Classification Types**: Must be one of 6 valid types
2. **Confidence Scores**: Must be between 0.0 and 1.0
3. **Similarity Thresholds**: Grouping at 0.85, manual review at 0.5
4. **Kingdom Values**: Only "Plantae" or "Animalia" allowed
5. **Canonical Uniqueness**: Each canonical_id must be globally unique

### Data Quality Rules
1. **Non-empty Names**: recorded_by cannot be null or empty
2. **Valid Dates**: All dates must be valid and occurrence dates cannot be in future
3. **Positive Counts**: All count fields must be non-negative
4. **Referential Integrity**: All foreign keys must reference valid entities

### Performance Constraints
1. **Batch Size**: Maximum 5,000 records per batch for memory efficiency
2. **Checkpoint Frequency**: Every 10,000-25,000 records
3. **Index Requirements**: Indexes on document_id, canonical_id, kingdom, processing_status

## Storage Considerations

### MongoDB Collections
- **ocorrencias**: Source specimen records (existing)
- **coletores**: Canonical collectors and variations (existing)
- **classifications**: Classification results (new)
- **checkpoints**: Processing checkpoints (existing)
- **statistics**: Processing statistics (existing)

### Indexing Strategy
```javascript
// Recommended indexes for performance
db.ocorrencias.createIndex({"recordedBy": 1, "kingdom": 1})
db.coletores.createIndex({"canonical_id": 1})
db.coletores.createIndex({"sobrenome_normalizado": 1})
db.classifications.createIndex({"entity_type": 1, "confidence_score": -1})
db.checkpoints.createIndex({"process_type": 1, "created_at": -1})
```

## Implementation Notes

This data model supports the complete canonicalization workflow:
1. **Classification**: CollectorRecord → ClassificationResult
2. **Normalization**: Extract components for similarity calculation
3. **Canonicalization**: Group variations into CanonicalCollector
4. **Statistics**: Track KingdomStatistics for analysis
5. **Checkpointing**: Maintain ProcessingBatch and CheckpointData for recovery

The model balances flexibility for complex biological names with performance requirements for 11M+ record processing.