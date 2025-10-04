# Tasks: Sistema de Identificação e Canonicalização de Coletores de Plantas

**Input**: Design documents from `H:\git\coletoresBO\specs\001-especificacao-leia-o\`
**Prerequisites**: plan.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓

## Execution Flow (main)
```
1. Load plan.md from feature directory ✓
   → Tech stack: Python 3.11+, pymongo, pandas, NLP libraries, DuckDB, transformers+torch (NER)
   → Structure: Single project (src/, tests/, docs/)
2. Load design documents ✓
   → data-model.md: 6 entities (ClassificationResult, AtomizedName, etc.)
   → contracts/: pipeline_contracts.py (8 protocols + NER)
   → research.md: 8 technical decisions + NER model selection
   → quickstart.md: 7 acceptance scenarios
3. Generate tasks by category ✓
   → Setup: 5 tasks (project init, deps, config)
   → Tests: 14 tasks (7 contract including NER + 7 integration)
   → Core: 14 tasks (models, algorithms, pipeline stages, NER fallback)
   → Integration: 5 tasks (CLI, parallel processing, CSV export)
   → Polish: 5 tasks (unit tests, performance, docs)
4. Apply task rules ✓
   → Different files = [P] parallel
   → Same file = sequential
   → Tests before implementation (TDD)
5. Number tasks sequentially (T001-T040, T011a, T024a, T024b) ✓
6. Dependencies mapped ✓
7. Parallel execution examples included ✓
8. Validation ✓
   → All contracts have tests ✓
   → All entities have models ✓
   → All scenarios covered ✓
9. SUCCESS - Tasks ready for execution ✓
```

---

## Format: `[ID] [P?] Description`
- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions
Single project structure (data processing pipeline):
- Source: `src/` at repository root
- Tests: `tests/` at repository root
- Docs: `docs/` at repository root

---

## Phase 3.1: Setup & Infrastructure

### T001: Create project structure
**File**: Repository root
**Description**: Create directory structure matching plan.md:
```
src/
├── pipeline/
│   ├── __init__.py
│   ├── classifier.py
│   ├── atomizer.py
│   ├── normalizer.py
│   └── canonicalizer.py
├── algorithms/
│   ├── __init__.py
│   ├── similarity.py
│   └── phonetic.py
├── models/
│   ├── __init__.py
│   ├── entities.py
│   └── schemas.py
├── storage/
│   ├── __init__.py
│   ├── mongodb_client.py
│   └── local_db.py
├── cli.py
└── config.py

tests/
├── contract/
│   ├── __init__.py
│   ├── test_classification_schema.py
│   ├── test_atomization_schema.py
│   ├── test_normalization_schema.py
│   ├── test_canonicalization_schema.py
│   ├── test_entity_schema.py
│   └── test_csv_schema.py
├── integration/
│   ├── __init__.py
│   └── test_scenarios.py
└── unit/
    ├── __init__.py
    ├── test_classifier.py
    ├── test_atomizer.py
    ├── test_normalizer.py
    ├── test_canonicalizer.py
    └── test_algorithms.py

docs/
└── rules.md

data/  # Created at runtime for local DB
output/  # Created at runtime for CSV reports
```
**Dependencies**: None
**Acceptance**: All directories exist with __init__.py files where needed

---

### T002: Initialize Python 3.11+ project with dependencies
**File**: `requirements.txt`, `setup.py` or `pyproject.toml`
**Description**: Create dependency file with:
```
# Core dependencies
pymongo>=4.6.0
pydantic>=2.5.0
python-Levenshtein>=0.23.0
jellyfish>=1.0.0
duckdb>=0.10.0
pandas>=2.1.0
click>=8.1.0
tqdm>=4.66.0

# NER Model dependencies (fallback for low-confidence cases)
transformers>=4.35.0
torch>=2.1.0

# Development dependencies
pytest>=7.4.0
pytest-benchmark>=4.0.0
mypy>=1.7.0
black>=23.12.0
ruff>=0.1.0
```
Install with: `pip install -r requirements.txt`
**Dependencies**: T001 (project structure exists)
**Acceptance**: `pip list` shows all packages installed, `python --version` ≥3.11

---

### T003 [P]: Configure linting and type checking
**File**: `pyproject.toml`, `.ruff.toml`, `mypy.ini`
**Description**: Create configuration files:

`pyproject.toml`:
```toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W", "UP"]
ignore = []

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
```

`mypy.ini`:
```ini
[mypy]
python_version = 3.11
strict = True
warn_return_any = True
warn_unused_configs = True
```
**Dependencies**: T002 (tools installed)
**Acceptance**: `ruff check src/` runs, `mypy src/` runs, `black --check src/` runs

---

### T004 [P]: Create configuration file structure
**File**: `config.yaml`, `src/config.py`
**Description**:

`config.yaml`:
```yaml
mongodb:
  uri: "mongodb://localhost:27017"
  database: "plant_samples"
  collection: "specimens"
  filter: { kingdom: "Plantae" }

local_db:
  type: "duckdb"
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

`src/config.py`: Load YAML with pydantic-settings for type-safe config
**Dependencies**: T002 (pydantic installed)
**Acceptance**: `python -c "from src.config import Config; c = Config.from_yaml('config.yaml'); print(c.mongodb.uri)"` works

---

### T005 [P]: Setup DuckDB schema
**File**: `src/storage/local_db.py` (schema creation only)
**Description**: Create DuckDB schema from data-model.md:
```sql
CREATE TABLE IF NOT EXISTS canonical_entities (
    id INTEGER PRIMARY KEY,
  canonicalName TEXT NOT NULL,
  entityType TEXT NOT NULL CHECK(entityType IN ('Pessoa', 'GrupoPessoas', 'Empresa', 'NaoDeterminado')),
    classification_confidence REAL NOT NULL CHECK(classification_confidence >= 0.70 AND classification_confidence <= 1.0),
    grouping_confidence REAL NOT NULL CHECK(grouping_confidence >= 0.70 AND grouping_confidence <= 1.0),
    variations JSON NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_canonicalName_type ON canonical_entities(canonicalName, entityType);
CREATE INDEX IF NOT EXISTS idx_entityType ON canonical_entities(entityType);
```
Implement schema creation method only (no CRUD yet).
**Dependencies**: T002 (duckdb installed), T004 (config ready)
**Acceptance**: Running schema creation connects to DuckDB and creates table without errors

---

## Phase 3.2: Tests First (TDD) ⚠️ MUST COMPLETE BEFORE 3.3
**CRITICAL: These tests MUST be written and MUST FAIL before ANY implementation**

### T006 [P]: Contract test - Classification schema
**File**: `tests/contract/test_classification_schema.py`
**Description**: Test ClassificationInput/Output from pipeline_contracts.py:
- Valid input: `{"text": "Silva, J. & Forzza, R.C."}` → accepts
- Invalid input: `{"text": ""}` → rejects (min_length=1)
- Valid output: category in enum, confidence 0.0-1.0, should_atomize bool
- Below threshold: confidence < 0.70 → raises ValueError
Use Pydantic validation, pytest parametrize for test cases.
**Dependencies**: T002 (pytest installed)
**Acceptance**: Test runs, ALL assertions FAIL (no implementation yet)

---

### T007 [P]: Contract test - Atomization schema
**File**: `tests/contract/test_atomization_schema.py`
**Description**: Test AtomizationInput/Output from pipeline_contracts.py:
- Valid input: text + category
- Valid output: atomized_names list with AtomizedName objects
- AtomizedName fields: text (min_length=1), original_formatting, position (≥0), separator_used enum
- Empty list for non-ConjuntoPessoas categories
**Dependencies**: T002
**Acceptance**: Test runs, assertions FAIL (no implementation)

---

### T008 [P]: Contract test - Normalization schema
**File**: `tests/contract/test_normalization_schema.py`
**Description**: Test NormalizationInput/Output from pipeline_contracts.py:
- Valid input: original_name (min_length=1)
- Valid output: normalized MUST be uppercase, rules_applied list
- Invalid: normalized not uppercase → validation fails
**Dependencies**: T002
**Acceptance**: Test runs, assertions FAIL

---

### T009 [P]: Contract test - Canonicalization schema
**File**: `tests/contract/test_canonicalization_schema.py`
**Description**: Test CanonicalizationInput/Output from pipeline_contracts.py:
- Valid input: normalized_name, entityType, classification_confidence ≥0.70
- Valid output: CanonicalEntity with grouping_confidence ≥0.70, variations min_length=1
- Invalid: grouping_confidence < 0.70 → raises ValueError
**Dependencies**: T002
**Acceptance**: Test runs, assertions FAIL

---

### T010 [P]: Contract test - Entity schema
**File**: `tests/contract/test_entity_schema.py`
**Description**: Test CanonicalEntity and NameVariation from pipeline_contracts.py:
- CanonicalEntity: all confidence fields ≥0.70, variations non-empty
- NameVariation: occurrence_count ≥1, association_confidence ≥0.70
- Datetime fields populated
**Dependencies**: T002
**Acceptance**: Test runs, assertions FAIL

---

### T011 [P]: Contract test - CSV export schema
**File**: `tests/contract/test_csv_schema.py`
**Description**: Test CSVReportRow from pipeline_contracts.py:
- Valid row: canonicalName, semicolon-separated variations, semicolon-separated counts
- Count alignment: len(variations.split(';')) == len(occurrenceCounts.split(';'))
- No confidence fields in CSV (per FR-025)
**Dependencies**: T002
**Acceptance**: Test runs, assertions FAIL

---

### T011a [P]: Contract test - NER fallback schema
**File**: `tests/contract/test_ner_schema.py`
**Description**: Test NER fallback input/output schemas:
- Valid input: text (string), original_confidence (0.0-1.0)
- Valid output: entities list with (text, label, score), improved_confidence (0.0-1.0)
- Trigger condition: original_confidence < 0.70
- NER labels: PESSOA, ORGANIZATION, etc.
**Dependencies**: T002
**Acceptance**: Test runs, assertions FAIL

---

### T012 [P]: Integration test - Scenario 1 (ConjuntoPessoas)
**File**: `tests/integration/test_scenarios.py::test_scenario_1_conjunto_pessoas`
**Description**: From quickstart.md Scenario 1:
- Input: "Silva, J. & R.C. Forzza; Santos, M. et al."
- Assert: category == ConjuntoPessoas, confidence ≥0.90
- Assert: atomized == ["Silva, J.", "R.C. Forzza", "Santos, M."]
Use Classifier and Atomizer (not yet implemented).
**Dependencies**: T002
**Acceptance**: Test written, FAILS with ImportError or NotImplementedError

---

### T013 [P]: Integration test - Scenario 2 (Variation grouping)
**File**: `tests/integration/test_scenarios.py::test_scenario_2_variation_grouping`
**Description**: From quickstart.md Scenario 2:
- Inputs: ["Forzza, R.C.", "Forzza, R.", "R.C. Forzza", "Rafaela C. Forzza"]
- Process through Normalizer → Canonicalizer
- Assert: All map to same canonical name "Forzza, R.C."
**Dependencies**: T002
**Acceptance**: Test written, FAILS (no implementation)

---

### T014 [P]: Integration test - Scenarios 3-5 (Classification categories)
**File**: `tests/integration/test_scenarios.py::test_scenario_3_grupo_pessoas`, `test_scenario_4_empresa`, `test_scenario_5_nao_determinado`
**Description**: From quickstart.md Scenarios 3-5:
- Scenario 3: "Pesquisas da Biodiversidade" → GrupoPessoas
- Scenario 4: "EMBRAPA", "USP" → Empresa
- Scenario 5: "?", "sem coletor" → NaoDeterminado
Use Classifier (not yet implemented).
**Dependencies**: T002
**Acceptance**: Tests written, all FAIL

---

### T015 [P]: Integration test - Scenario 6 (Dynamic DB updates)
**File**: `tests/integration/test_scenarios.py::test_scenario_6_dynamic_updates`
**Description**: From quickstart.md Scenario 6:
- Start with empty database
- Process batch of records incrementally
- Assert: Database entity count increases
Use LocalDatabase.get_all_entities() (not yet implemented).
**Dependencies**: T002, T005 (DB schema exists)
**Acceptance**: Test written, FAILS

---

### T016 [P]: Integration test - Scenario 7 (CSV export)
**File**: `tests/integration/test_scenarios.py::test_scenario_7_csv_export`
**Description**: From quickstart.md Scenario 7:
- Export to CSV using LocalDatabase.export_to_csv()
- Assert: 3 columns (canonicalName, variations, occurrenceCounts)
- Assert: No confidence columns
- Assert: Semicolon-separated values, counts align with variations
**Dependencies**: T002, T005
**Acceptance**: Test written, FAILS

---

### T017 [P]: Integration test - Performance validation
**File**: `tests/integration/test_scenarios.py::test_performance_target`
**Description**: From quickstart.md Performance Validation:
- Process 100K test records
- Measure records/sec
- Assert: ≥213 records/sec (6-hour target for 4.6M records)
Use pytest-benchmark for timing.
**Dependencies**: T002
**Acceptance**: Test written, FAILS (no pipeline yet)

---

### T018 [P]: Unit test - Similarity algorithms
**File**: `tests/unit/test_algorithms.py`
**Description**: From research.md Section 2:
- Test Levenshtein distance: known pairs → expected scores
- Test Jaro-Winkler: short string optimization
- Test Phonetic (Metaphone): "Silva" vs "Sylva" → same phonetic code
- Test combined similarity_score: weighted average (0.4, 0.4, 0.2)
- Performance: Assert each comparison <1ms (pytest-benchmark)
**Dependencies**: T002
**Acceptance**: Test written, FAILS (algorithms not implemented)

---

## Phase 3.3: Core Implementation (ONLY after tests T006-T018 are failing)

### T019 [P]: Implement Pydantic models
**File**: `src/models/entities.py`, `src/models/schemas.py`
**Description**: From data-model.md:
- `entities.py`: EntityType, ClassificationCategory enums, ClassificationResult, NormalizedName, CanonicalEntity, NameVariation models (Pydantic BaseModel)
- `schemas.py`: Input/output schemas matching pipeline_contracts.py
- Add field validators: confidence ≥0.70, normalized MUST be uppercase, occurrence_count ≥1
**Dependencies**: T006-T011 (contract tests failing)
**Acceptance**: Contract tests T006-T011 PASS, mypy src/models/ passes

---

### T020 [P]: Implement similarity algorithms
**File**: `src/algorithms/similarity.py`, `src/algorithms/phonetic.py`
**Description**: From research.md Section 2:
- `similarity.py`:
  - `levenshtein_score(s1, s2) -> float` using python-Levenshtein
  - `jaro_winkler_score(s1, s2) -> float` using jellyfish
  - `similarity_score(s1, s2) -> float`: weighted combo (0.4, 0.4, 0.2)
- `phonetic.py`:
  - `phonetic_match(s1, s2) -> bool` using jellyfish.metaphone
**Dependencies**: T018 (unit test failing), T002 (libraries installed)
**Acceptance**: T018 unit test PASSES, all comparisons <1ms

---

### T021: Implement Classifier
**File**: `src/pipeline/classifier.py`
**Description**: From research.md Section 4 and quickstart.md:
- Implement ClassifierProtocol from pipeline_contracts.py
- `classify(ClassificationInput) -> ClassificationOutput`
- Pattern hierarchy (checked in order):
  1. NãoDeterminado: exact match ("?", "sem coletor")
  2. Empresa: all-caps acronyms, institution keywords
  3. ConjuntoPessoas: separators (`;`, `&`, `et al.`) + name patterns
  4. Pessoa: single name pattern (surname + initials or full name)
  5. GrupoPessoas: generic group terms, no proper names
- Confidence scoring per research.md (exact match +0.3, multiple indicators +0.1, ambiguity -0.2)
- **NER Fallback Integration**: If confidence < 0.70, call NER fallback (T024a) to improve classification
- Raise ValueError if confidence still < 0.70 after NER attempt
**Dependencies**: T012, T014 (integration tests failing), T019 (models ready), T024a (NER fallback)
**Acceptance**: T012 Scenario 1 classification PASSES, T014 Scenarios 3-5 PASS, low-confidence cases use NER

---

### T022: Implement Atomizer
**File**: `src/pipeline/atomizer.py`
**Description**: From spec FR-008 to FR-010:
- Implement AtomizerProtocol from pipeline_contracts.py
- `atomize(AtomizationInput) -> AtomizationOutput`
- If category != ConjuntoPessoas: return empty atomized_names list
- Else: split by separators `;`, `&`, `et al.`
- Preserve original formatting, assign position (0-indexed), record separator used
- Return list of AtomizedName objects
**Dependencies**: T012 (integration test failing), T019 (models ready)
**Acceptance**: T012 Scenario 1 atomization PASSES (["Silva, J.", "R.C. Forzza", "Santos, M."])

---

### T023: Implement Normalizer
**File**: `src/pipeline/normalizer.py`
**Description**: From research.md Section 1 and FR-012:
- Implement NormalizerProtocol from pipeline_contracts.py
- `normalize(NormalizationInput) -> NormalizationOutput`
- Rules (from clarification Session 2025-10-03):
  1. Remove extra whitespace: `' '.join(text.split())`
  2. Standardize punctuation: `re.sub(r'\s*([,;.&])\s*', r'\1 ', text)`
  3. Uppercase for comparison: `text.upper()`
- Record rules_applied list
**Dependencies**: T013 (integration test failing), T019 (models ready)
**Acceptance**: T013 Scenario 2 normalization step PASSES (all variations normalized to uppercase)

---

### T024: Implement Canonicalizer
**File**: `src/pipeline/canonicalizer.py`
**Description**: From spec FR-013 to FR-016 and research.md Section 2:
- Implement CanonicalizerProtocol from pipeline_contracts.py
- `canonicalize(CanonicalizationInput) -> CanonicalizationOutput`
- Use LocalDatabase.find_similar_entities(normalized_name, entityType, threshold=0.70)
- If similar entity found (similarity ≥0.70): update variations, return is_new_entity=False
- Else: create new CanonicalEntity with canonicalName in "Sobrenome, Iniciais" format (for Pessoa)
- Calculate grouping_confidence using similarity_score from algorithms
- Raise ValueError if grouping_confidence < 0.70
**Dependencies**: T013 (integration test failing), T019 (models), T020 (similarity algorithms), T025 (LocalDatabase)
**Acceptance**: T013 Scenario 2 PASSES (all variations grouped under "Forzza, R.C.")

---

### T024a [P]: Implement NER Fallback
**File**: `src/pipeline/ner_fallback.py`
**Description**: From PRD NER requirements:
- Implement NER fallback using transformers library
- Load model: `pierreguillou/bert-base-cased-pt-lenerbr` (Portuguese BERT NER)
- `classify_with_ner(text: str, original_confidence: float) -> NEROutput`
- Trigger: Called only when original_confidence < 0.70
- Extract entities with label PESSOA (person names)
- Return improved classification with entities and confidence boost
- Cache model in memory (load once at initialization)
- Add timeout (max 5s per inference) for performance
**Dependencies**: T002 (transformers installed), T011a (contract test), T019 (models)
**Acceptance**: Can load BERT model, extract PESSOA entities, T011a contract test PASSES

---

### T024b: Unit test - NER fallback
**File**: `tests/unit/test_ner_fallback.py`
**Description**: Test NER fallback functionality:
- Test model loading and caching
- Test entity extraction: known names → PESSOA labels
- Test confidence improvement: low confidence (0.65) → boosted (0.80+)
- Test performance: inference <5s per string
- Test edge cases: empty string, Unicode, special characters
**Dependencies**: T024a (NER implemented)
**Acceptance**: All tests PASS, performance <5s

---

### T025 [P]: Implement MongoDB client
**File**: `src/storage/mongodb_client.py`
**Description**: From spec FR-017, FR-018:
- Implement MongoDBSourceProtocol from pipeline_contracts.py
- `stream_records(batch_size=1000)`: yield batches where kingdom=="Plantae"
- `get_total_count() -> int`: count of Plantae records for progress tracking
- Use pymongo cursor with `batch_size` for memory efficiency
**Dependencies**: T002 (pymongo installed), T004 (config ready)
**Acceptance**: Can connect to test MongoDB, stream records in batches, count returns correct value

---

### T026: Implement LocalDatabase CRUD
**File**: `src/storage/local_db.py` (extend from T005)
**Description**: From spec FR-022 to FR-024:
- Implement LocalDatabaseProtocol from pipeline_contracts.py
- `upsert_entity(CanonicalEntity) -> CanonicalEntity`: Insert new or update existing
  - Update: increment variation occurrence_count, update last_seen timestamp
- `find_similar_entities(normalized_name, entityType, threshold=0.70) -> List[tuple[CanonicalEntity, float]]`:
  - Load all entities of same type, calculate similarity scores, return those ≥threshold
- `get_all_entities() -> List[CanonicalEntity]`: Retrieve all for CSV export
- JSON handling: serialize/deserialize variations array
**Dependencies**: T005 (schema created), T019 (models), T020 (similarity for find_similar)
**Acceptance**: Can insert entity, find similar, retrieve all, T015 Scenario 6 PASSES

---

### T027: Implement CSV export
**File**: `src/storage/local_db.py::export_to_csv`
**Description**: From spec FR-025:
- Implement `export_to_csv(output_path: str) -> None`
- Retrieve all entities, format as CSVReportRow:
  - canonicalName: entity.canonicalName
  - variations: ";".join([v.variation_text for v in entity.variations])
  - occurrenceCounts: ";".join([str(v.occurrence_count) for v in entity.variations])
- Write to CSV with pandas (3 columns, NO confidence scores)
**Dependencies**: T026 (CRUD ready), T002 (pandas installed)
**Acceptance**: T016 Scenario 7 PASSES (CSV format valid, no confidence columns)

---

### T028: Implement CLI orchestrator
**File**: `src/cli.py`
**Description**: From spec and quickstart.md:
- Main entry point: `run_pipeline(config_path, batch_size, workers, output_csv)`
- Load config from YAML
- Initialize MongoDB client, LocalDatabase, NER fallback model (lazy load)
- Orchestrate pipeline: MongoDBRecord → Classify (with NER fallback if needed) → Atomize → Normalize → Canonicalize → Store
- Return PipelineResult with metrics (total_records, processed, elapsed_time, ner_fallback_count)
- Use click for CLI arguments
**Dependencies**: T021-T027, T024a (all pipeline stages + NER implemented)
**Acceptance**: Can run `python src/cli.py --config config.yaml`, processes test records end-to-end, NER triggered for low-confidence

---

### T029: Implement parallel processing
**File**: `src/cli.py` (extend from T028)
**Description**: From spec FR-021 and research.md Section 5:
- Add multiprocessing.Pool with configurable worker count
- Batch partitioning: divide records into chunks, distribute to workers
- Each worker: process batch through full pipeline (classify → atomize → normalize → canonicalize)
- Results aggregator: merge to LocalDatabase with thread-safe writes (DuckDB WAL mode or locks)
- Monitor: tqdm progress bar, records/sec metric, ETA calculation
**Dependencies**: T028 (CLI orchestrator ready)
**Acceptance**: Processing with workers=8 achieves ≥213 rec/sec, T017 performance test PASSES

---

### T030: Implement error handling and logging
**File**: `src/cli.py`, all pipeline stages
**Description**: From constitution UX requirements:
- Add try/except for DB connection failures, low-confidence results
- User-friendly error messages (no stack traces in CLI output)
- Logging: log low-confidence classifications (<0.70) to file for manual review
- Progress indicators for 6-hour processing
**Dependencies**: T028 (CLI exists)
**Acceptance**: DB connection error shows helpful message, low-confidence items logged, no crashes

---

## Phase 3.4: Integration & Validation

### T031: Create rules documentation template
**File**: `docs/rules.md`
**Description**: From spec FR-026, FR-027:
- Document classification patterns (NãoDeterminado, Empresa, ConjuntoPessoas, Pessoa, GrupoPessoas)
- Document NER fallback: trigger condition (<0.70), model used (pierreguillou/bert-base-cased-pt-lenerbr), expected boost
- Document atomization separators (`;`, `&`, `et al.`)
- Document normalization rules (spaces, punctuation, uppercase)
- Document canonicalization format ("Sobrenome, Iniciais")
- Document similarity algorithm weights (Levenshtein 0.4, Jaro-Winkler 0.4, Phonetic 0.2)
- Mark as editable for algorithm refinement
**Dependencies**: T021-T024, T024a (pipeline stages + NER implemented)
**Acceptance**: docs/rules.md exists, clearly documents all algorithm rules including NER fallback

---

### T032: End-to-end integration test
**File**: `tests/integration/test_e2e_pipeline.py`
**Description**:
- Insert 1000 test specimens to MongoDB (include low-confidence cases to trigger NER)
- Run full pipeline: `run_pipeline(config_path, batch_size=100, workers=4)`
- Assert: All stages complete (classification with NER fallback, atomization, normalization, canonicalization)
- Assert: NER fallback triggered for low-confidence cases (check ner_fallback_count > 0)
- Assert: Local DB has entities, CSV exported
- Assert: No errors or exceptions
**Dependencies**: T028-T030 (full pipeline ready)
**Acceptance**: E2E test PASSES, processes 1000 records successfully

---

### T033: Validate all acceptance scenarios
**File**: Run quickstart.md manually
**Description**:
- Follow quickstart.md steps exactly
- Insert test specimens to MongoDB
- Run each scenario validation (1-7) from quickstart
- Assert: All assertions PASS
- Check performance: ≥213 rec/sec
**Dependencies**: T032 (E2E passing)
**Acceptance**: All quickstart.md scenarios ✓, performance target met ✓

---

### T034: Constitution compliance check
**File**: Run static analysis tools
**Description**: From constitution Code Quality Standards:
- Run `mypy src/ --strict`: Zero type errors
- Run `ruff check src/`: Zero linting errors
- Run `black --check src/`: Zero formatting issues
- Check docstrings: All public APIs have complete docstrings (Google style)
- Check complexity: No functions >50 lines or cyclomatic complexity >10 (use radon if needed)
**Dependencies**: T003 (tools configured), T028 (implementation complete)
**Acceptance**: All tools pass, no violations

---

### T035: Test coverage validation
**File**: Run pytest with coverage
**Description**: From constitution TDD requirements:
- Run `pytest --cov=src --cov-report=term-missing`
- Assert: Total coverage ≥80%
- Assert: Business logic coverage (pipeline/, algorithms/) = 100%
- Assert: All contract tests PASS
- Assert: All integration tests PASS
**Dependencies**: T019-T030 (all implementation), T006-T018 (all tests)
**Acceptance**: Coverage ≥80%, business logic 100%, all tests green ✓

---

## Phase 3.5: Polish & Documentation

### T036 [P]: Add unit tests for edge cases
**File**: `tests/unit/test_classifier.py`, `test_atomizer.py`, `test_normalizer.py`, `test_canonicalizer.py`
**Description**:
- Classifier edge cases: empty strings, Unicode, mixed patterns
- Atomizer edge cases: no separators, malformed "et al."
- Normalizer edge cases: excessive whitespace, special chars
- Canonicalizer edge cases: exact duplicates, near-threshold similarity (0.69 vs 0.71)
**Dependencies**: T021-T024 (stages implemented)
**Acceptance**: Edge case tests PASS, coverage increases

---

### T037 [P]: Performance benchmarking
**File**: `tests/unit/test_algorithms.py` (extend)
**Description**: Using pytest-benchmark:
- Benchmark similarity_score: <1ms per comparison (from research.md)
- Benchmark full pipeline single record: <5ms end-to-end
- Benchmark batch processing: 100K records → validate ≥213 rec/sec
- If below target: tune worker count, batch size
**Dependencies**: T020 (algorithms), T029 (parallel processing)
**Acceptance**: All benchmarks meet targets, T017 performance test PASSES

---

### T038 [P]: Create README
**File**: `README.md`
**Description**:
- Project overview: NLP pipeline for plant collector canonicalization with NER fallback
- Installation: Python 3.11+, `pip install -r requirements.txt` (includes BERT model download)
- Configuration: How to edit config.yaml (NER fallback settings)
- Usage: `python src/cli.py --config config.yaml --workers 8`
- Testing: `pytest tests/`
- Performance: Expected 213 rec/sec, 6-hour processing for 4.6M records (NER adds ~2s per low-confidence case)
- Output: CSV format (canonicalName, variations, counts), local DB location
- NER Fallback: Explain when triggered, model used, expected accuracy improvement
**Dependencies**: T028 (CLI ready)
**Acceptance**: README complete, clear usage instructions including NER details

---

### T039 [P]: Remove code duplication
**File**: All `src/` files
**Description**: From constitution DRY principle:
- Scan for duplicate code blocks (>3 similar blocks)
- Extract shared logic to utility functions
- Common candidates: confidence threshold checking, normalization helpers, JSON serialization
- Ensure no regression: all tests still PASS after refactoring
**Dependencies**: T035 (all tests passing)
**Acceptance**: No DRY violations (ruff or manual review), tests still green

---

### T040: Final validation checklist
**File**: Manual verification
**Description**: Run complete validation per quickstart.md Success Criteria:
- ✅ All 7 acceptance scenarios PASS
- ✅ Performance target met (≥213 rec/sec)
- ✅ Full E2E pipeline completes without errors
- ✅ Output artifacts generated (CSV, local DB, rules.md)
- ✅ All confidence thresholds enforced (≥0.70)
- ✅ Constitution compliance (mypy, ruff, black, coverage ≥80%)
- ✅ README and docs complete
**Dependencies**: T033-T039 (all polish complete)
**Acceptance**: All ✅ checked, ready for production

---

## Dependencies Graph

```
Setup Phase:
T001 → T002 → T003, T004, T005
        ↓
Tests Phase (all parallel after T002):
T006, T007, T008, T009, T010, T011, T011a (contract tests - T011a for NER)
T012, T013, T014, T015, T016, T017 (integration tests)
T018 (unit tests)
        ↓
Core Implementation:
T019 (models) ← [blocks] → T020 (algorithms)
        ↓                      ↓
T024a (NER fallback) [P] ← T002, T011a, T019
T024b (NER unit test) ← T024a
        ↓
T021 (Classifier) ← T012, T014, T024a (NER integration)
T022 (Atomizer) ← T012
T023 (Normalizer) ← T013
T024 (Canonicalizer) ← T013, T020
T025 (MongoDB client)
T026 (LocalDB CRUD) ← T005, T019, T020
T027 (CSV export) ← T026
        ↓
Integration:
T028 (CLI) ← T021-T027, T024a (NER included)
T029 (Parallel) ← T028
T030 (Error handling) ← T028
        ↓
Validation:
T031 (Rules doc) ← T024a (NER docs)
T032 (E2E test) ← T028-T030 (NER fallback tested)
T033 (Quickstart validation) ← T032
T034 (Constitution check) ← T003, T028
T035 (Coverage) ← T006-T030, T024a, T024b
        ↓
Polish:
T036, T037, T038, T039 (all parallel after T035)
T040 (Final validation) ← T033-T039
```

---

## Parallel Execution Examples

### Example 1: Contract Tests (T006-T011)
All contract tests can run in parallel (different files, no dependencies):
```bash
# Launch all contract tests together
pytest tests/contract/ -n 6  # pytest-xdist for parallel execution
```

### Example 2: Core Models & Algorithms (T019-T020)
Models and algorithms are independent (different files):
```bash
# Task 1: Implement Pydantic models in src/models/
# Task 2: Implement similarity algorithms in src/algorithms/
# These can be worked on simultaneously by different developers
```

### Example 3: Unit Tests & Docs (T036-T039)
Polish tasks are mostly independent:
```bash
# Task 1: Add edge case unit tests
# Task 2: Run performance benchmarks
# Task 3: Create README
# Task 4: Remove duplication
# All [P] - can run in parallel
```

---

## Task Validation Checklist
*GATE: Verified before task execution*

- [x] All contracts have corresponding tests (T006-T011 cover pipeline_contracts.py)
- [x] All entities have model tasks (T019 implements all from data-model.md)
- [x] All tests come before implementation (T006-T018 before T019-T030)
- [x] Parallel tasks truly independent (all [P] tasks touch different files)
- [x] Each task specifies exact file path (✓ all tasks have file paths)
- [x] No task modifies same file as another [P] task (verified: no conflicts)

---

## Notes
- **[P] tasks**: Different files, no dependencies, can run in parallel
- **TDD strict**: T006-T018, T011a MUST be written and MUST FAIL before T019+ implementation
- **NER Fallback**: Triggered only for confidence <0.70, uses BERT model pierreguillou/bert-base-cased-pt-lenerbr
- **Commit after each task**: Atomic commits for rollback capability
- **Performance target**: ≥213 records/sec (validates 6-hour processing for 4.6M records, NER adds ~2s overhead per low-confidence case)
- **Confidence threshold**: All scores ≥0.70 (enforced in validation, NER helps achieve this)
- **Avoid**: Vague tasks, same file conflicts, implementation before tests

---

## Estimated Timeline
- **Phase 3.1 (Setup)**: T001-T005 → ~2 hours
- **Phase 3.2 (Tests)**: T006-T018, T011a → ~9 hours (14 test files including NER contract test)
- **Phase 3.3 (Core)**: T019-T030, T024a, T024b → ~19 hours (14 implementation tasks including NER fallback + unit test)
- **Phase 3.4 (Integration)**: T031-T035 → ~4 hours (validation)
- **Phase 3.5 (Polish)**: T036-T040 → ~4 hours (final touches)

**Total**: ~38 hours development time (with parallel execution, can compress to ~22-26 hours wall-clock time)
**NER Impact**: +3 hours for implementation, +2s per low-confidence record at runtime

---

**Ready for execution** - Start with T001 (project structure creation).
