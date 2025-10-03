# Research: Sistema de Identificação e Canonicalização de Coletores

## Overview
Research findings for building a robust NLP pipeline to classify, atomize, normalize, and canonicalize plant collector names from 4.6M MongoDB records.

---

## 1. Text Normalization for Name Matching

### Decision: Remove extra spaces + standardize punctuation + uppercase conversion

**Rationale**:
- Case-insensitive matching is essential for names (e.g., "SILVA, J." vs "Silva, J.")
- Punctuation standardization handles variations like "Silva,J" vs "Silva, J."
- Preserves original formatting for display while normalizing for comparison

**Implementation Approach**:
```python
def normalize(text: str) -> str:
    # Remove extra whitespace
    text = ' '.join(text.split())
    # Standardize punctuation spacing
    text = re.sub(r'\s*([,;.&])\s*', r'\1 ', text)
    # Uppercase for comparison
    return text.upper().strip()
```

**Alternatives Considered**:
- Unicode normalization (NFKD): Rejected - may lose important diacritics in Brazilian names
- Accent removal: Rejected - "José" and "Jose" are different people
- Abbreviation expansion: Rejected - too many edge cases, clarified as out of scope

---

## 2. Similarity Algorithms for Name Grouping

### Decision: Levenshtein + Jaro-Winkler + Phonetic (Soundex/Metaphone)

**Rationale**:
- **Levenshtein**: Handles character transpositions, typos (e.g., "Forzza" vs "Forza")
- **Jaro-Winkler**: Optimized for short strings, gives higher weight to prefix matches (important for surnames)
- **Phonetic (Metaphone)**: Catches phonetically similar names (e.g., "Silva" vs "Sylva")
- Combined scoring reduces false positives while catching valid variations

**Implementation Approach**:
```python
def similarity_score(str1: str, str2: str) -> float:
    # Normalize inputs
    s1, s2 = normalize(str1), normalize(str2)

    # Calculate individual scores
    lev_score = 1 - (levenshtein(s1, s2) / max(len(s1), len(s2)))
    jw_score = jaro_winkler(s1, s2)
    phonetic_score = 1.0 if metaphone(s1) == metaphone(s2) else 0.0

    # Weighted average (tunable)
    return (lev_score * 0.4) + (jw_score * 0.4) + (phonetic_score * 0.2)
```

**Libraries**:
- `python-Levenshtein`: Fast C implementation of edit distance
- `jellyfish`: Provides Jaro-Winkler and Metaphone/Soundex
- Performance: All algorithms O(n²) worst case, but fast for short strings (names <50 chars)

**Alternatives Considered**:
- Cosine similarity + TF-IDF: Rejected - overkill for short name strings
- Fuzzy matching only: Rejected - misses phonetic variations
- Deep learning (Siamese networks): Rejected - requires training data, overcomplicated

---

## 3. Local Database Schema

### Decision: Single denormalized table with embedded variation arrays

**Rationale**:
- Simplifies queries: Single table scan for reporting
- Efficient for write-heavy workload: Dynamic updates during 6-hour processing
- JSON support in SQLite (≥3.38) or native DuckDB JSON handles embedded arrays
- No JOIN overhead for CSV export

**Schema Design**:
```sql
CREATE TABLE canonical_entities (
    id INTEGER PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    entity_type TEXT NOT NULL, -- Pessoa|Grupo|Instituição|NãoDeterminado
    classification_confidence REAL NOT NULL,
    grouping_confidence REAL NOT NULL,
    variations JSON NOT NULL, -- [{"text": "...", "count": N, "confidence": 0.0-1.0}]
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_canonical_name ON canonical_entities(canonical_name);
CREATE INDEX idx_entity_type ON canonical_entities(entity_type);
```

**Storage Technology**:
- **DuckDB preferred**: Better JSON performance, analytical queries, in-process (no server)
- **SQLite fallback**: Universal, stable, good enough for 500K entities

**Alternatives Considered**:
- Normalized (entities + variations tables): Rejected - JOIN overhead, more complex writes
- Document DB (MongoDB locally): Rejected - redundant with source, heavier footprint
- Plain JSON file: Rejected - no indexing, slow lookups during incremental updates

---

## 4. Classification Algorithm (5 Categories)

### Decision: Rule-based pattern matching with confidence scoring

**Rationale**:
- Deterministic and explainable (required for "editable rules documentation")
- Pattern-based approach maps directly to spec categories
- Confidence scoring via pattern strength and ambiguity detection

**Pattern Hierarchy** (checked in order):
1. **Não determinado**: Exact matches (`?`, `sem coletor`, `não identificado`) → confidence 1.0
2. **Empresa/Instituição**: All-caps acronyms (≥2 chars), known institution keywords → confidence 0.8-1.0
3. **Conjunto de Pessoas**: Contains separators (`;`, `&`, `et al.`) + name patterns → confidence 0.9-1.0
4. **Pessoa**: Single name pattern (surname + initials, or full name) → confidence 0.7-0.95
5. **Grupo de Pessoas**: Generic group terms, no proper name patterns → confidence 0.7-0.9

**Name Pattern Detection**:
- Regex for "Surname, Initials" format: `r'^[A-Z][a-z]+(?:-[A-Z][a-z]+)?,\s*[A-Z]\.(?:[A-Z]\.)*$'`
- Initials pattern: `r'\b[A-Z]\.[A-Z]\.?\b'`
- Separator detection: `r'[;&]|et\s+al\.?'`

**Confidence Factors**:
- Exact pattern match: +0.3
- Multiple indicators: +0.1 per indicator (max 0.2)
- Ambiguity (mixed patterns): -0.2

**Alternatives Considered**:
- ML classifier (NER): Rejected - requires labeled training data, black box
- Probabilistic model (HMM/CRF): Rejected - overcomplicated for 5 clear categories
- Keyword lists: Rejected - too brittle, doesn't generalize

---

## 5. Parallel Processing Strategy

### Decision: Multiprocessing with batch partitioning

**Rationale**:
- **Target**: 213 records/sec → 4-8 worker processes on modern CPU achieves this
- Python GIL limits threading for CPU-bound similarity calculations
- Batch partitioning: Divide 4.6M records into chunks, process independently, merge results

**Architecture**:
```
MongoDB (4.6M records)
    ↓
Batch Reader (chunks of 10K records)
    ↓
Worker Pool (multiprocessing.Pool, 4-8 workers)
    ↓ [classify → atomize → normalize → canonicalize per batch]
    ↓
Results Aggregator (merge to local DB with locks)
    ↓
Local DuckDB (canonical entities)
```

**Libraries**:
- `multiprocessing.Pool`: Python stdlib, proven for CPU-bound tasks
- `pymongo` cursor batching: `batch_size=1000` to stream without loading all to RAM
- SQLite/DuckDB with WAL mode: Supports concurrent reads, serialized writes

**Performance Validation**:
- Benchmark single worker: If ≥27 rec/sec → 8 workers meet 6hr target
- Monitor: Progress bar (tqdm), ETA calculation, records/sec metric

**Alternatives Considered**:
- Threading: Rejected - GIL bottleneck for CPU-heavy similarity algorithms
- Async (asyncio): Rejected - no I/O bound work (MongoDB cursor is blocking)
- Dask/Ray: Rejected - overhead not justified for single-machine processing

---

## 6. Testing Strategy

### Contract Tests
- **Input schema**: String → Classification result (category + confidence)
- **Entity schema**: Canonical entity structure (name, type, confidences, variations)
- **Output schema**: CSV format validation (3 columns: canonical, variations, counts)
- Tools: Pydantic for schema validation, pytest parametrize for test cases

### Integration Tests (from Acceptance Scenarios)
1. "Silva, J. & R.C. Forzza; Santos, M. et al." → conjunto_pessoas, atomized correctly
2. Multiple variations grouped under single canonical name
3. "Pesquisas da Biodiversidade" → grupo_pessoas
4. "EMBRAPA" → empresa/instituição
5. "?" → não determinado
6. 4.6M records processed, DB updated dynamically
7. CSV report generated with correct format

### Unit Tests
- Each pipeline stage (classifier, atomizer, normalizer, canonicalizer) tested in isolation
- Similarity algorithms: Known input pairs → expected scores
- Edge cases: Empty strings, Unicode, malformed names

### Performance Tests
- `pytest-benchmark`: Similarity algorithm latency (<1ms per comparison)
- Integration benchmark: 1000 records end-to-end (<5 seconds = meets 213 rec/sec target)

---

## 7. Python Ecosystem & Dependencies

### Core Libraries
- **pymongo** (4.6+): MongoDB client with async support
- **pydantic** (2.5+): Schema validation, type safety
- **python-Levenshtein** (0.23+): Fast edit distance (C extension)
- **jellyfish** (1.0+): Jaro-Winkler, Metaphone, Soundex
- **duckdb** (0.10+): Embedded analytical DB with JSON support
- **pandas** (2.1+): CSV export, data manipulation
- **click** (8.1+): CLI framework with progress bars

### Development Tools
- **pytest** (7.4+): Test framework
- **pytest-benchmark**: Performance testing
- **mypy** (1.7+): Static type checking (strict mode)
- **black** (23.12+): Code formatting
- **ruff** (0.1+): Fast linting (replaces flake8, pylint)

### Python Version
- **3.11+**: Required for improved performance (10-60% faster than 3.10), better typing

---

## 8. Configuration Management

### Decision: YAML config + environment variables

**Config Structure**:
```yaml
mongodb:
  uri: "mongodb://localhost:27017"
  database: "plant_samples"
  collection: "specimens"
  filter: { kingdom: "Plantae" }

local_db:
  type: "duckdb"  # or "sqlite"
  path: "./data/canonical_entities.db"

processing:
  batch_size: 10000
  workers: 8
  confidence_threshold: 0.70

algorithms:
  similarity_weights:
    levenshtein: 0.4
    jaro_winkler: 0.4
    phonetic: 0.2

output:
  csv_path: "./output/canonical_report.csv"
  rules_doc: "./docs/rules.md"
```

**Library**: `pydantic-settings` for type-safe config with env var overrides

---

## Summary

All technical uncertainties from spec have been resolved:
- ✅ Normalization rules: Spaces + punctuation + uppercase
- ✅ Similarity algorithms: Levenshtein + Jaro-Winkler + Phonetic
- ✅ Local DB schema: Single denormalized table with JSON arrays
- ✅ Classification approach: Rule-based pattern matching
- ✅ Parallel processing: Multiprocessing with batch partitioning
- ✅ Testing strategy: Contract + Integration + Unit + Performance
- ✅ Tech stack: Python 3.11, DuckDB, proven NLP libraries

**Ready for Phase 1**: Design data models and contracts.
