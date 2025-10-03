# Quickstart: Sistema de Identificação e Canonicalização de Coletores

## Purpose
Quick validation that the implemented pipeline meets all acceptance criteria from the specification. Run these tests to verify end-to-end functionality.

---

## Prerequisites

### Environment Setup
```bash
# 1. Python 3.11+ installed
python --version  # Should be ≥3.11

# 2. Install dependencies
pip install -r requirements.txt

# 3. MongoDB running with test data
# Ensure MongoDB is accessible at configured URI (default: localhost:27017)

# 4. Configuration file exists
cat config.yaml  # Verify mongodb, local_db, processing settings
```

### Test Data Setup
```python
# Insert test specimens to MongoDB (for acceptance scenario validation)
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017")
db = client["plant_samples"]
collection = db["specimens"]

test_specimens = [
    {"kingdom": "Plantae", "collector": "Silva, J. & R.C. Forzza; Santos, M. et al."},
    {"kingdom": "Plantae", "collector": "Forzza, R.C."},
    {"kingdom": "Plantae", "collector": "Forzza, R."},
    {"kingdom": "Plantae", "collector": "R.C. Forzza"},
    {"kingdom": "Plantae", "collector": "Rafaela C. Forzza"},
    {"kingdom": "Plantae", "collector": "Pesquisas da Biodiversidade"},
    {"kingdom": "Plantae", "collector": "EMBRAPA"},
    {"kingdom": "Plantae", "collector": "USP"},
    {"kingdom": "Plantae", "collector": "?"},
    {"kingdom": "Plantae", "collector": "sem coletor"},
]

collection.insert_many(test_specimens)
print(f"Inserted {len(test_specimens)} test specimens")
```

---

## Acceptance Scenario Validation

### Scenario 1: ConjuntoPessoas Classification & Atomization
**Given**: "Silva, J. & R.C. Forzza; Santos, M. et al."
**Expected**:
- Classification: `ConjuntoPessoas`
- Confidence: ≥ 0.90
- Atomized: `["Silva, J.", "R.C. Forzza", "Santos, M."]`

```python
from src.pipeline.classifier import Classifier
from src.pipeline.atomizer import Atomizer
from src.contracts.pipeline_contracts import ClassificationInput, AtomizationInput

# Test classification
classifier = Classifier()
result = classifier.classify(ClassificationInput(text="Silva, J. & R.C. Forzza; Santos, M. et al."))

assert result.category == "ConjuntoPessoas", f"Expected ConjuntoPessoas, got {result.category}"
assert result.confidence >= 0.90, f"Expected confidence ≥0.90, got {result.confidence}"
assert result.should_atomize == True, "Expected should_atomize=True"
print(f"✅ Scenario 1 - Classification: {result.category} (confidence: {result.confidence:.2f})")

# Test atomization
atomizer = Atomizer()
atomized = atomizer.atomize(AtomizationInput(text=result.original_text, category=result.category))

expected_names = ["Silva, J.", "R.C. Forzza", "Santos, M."]
actual_names = [n.text for n in atomized.atomized_names]
assert actual_names == expected_names, f"Expected {expected_names}, got {actual_names}"
print(f"✅ Scenario 1 - Atomization: {actual_names}")
```

---

### Scenario 2: Variation Grouping Under Canonical Name
**Given**: Multiple variations: "Forzza, R.C.", "Forzza, R.", "R.C. Forzza", "Rafaela C. Forzza"
**Expected**: All grouped under single canonical name "Forzza, R.C."

```python
from src.pipeline.canonicalizer import Canonicalizer
from src.pipeline.normalizer import Normalizer
from src.contracts.pipeline_contracts import NormalizationInput, CanonicalizationInput, EntityType

normalizer = Normalizer()
canonicalizer = Canonicalizer()

variations = ["Forzza, R.C.", "Forzza, R.", "R.C. Forzza", "Rafaela C. Forzza"]
canonical_entities = []

for variation in variations:
    # Normalize
    normalized = normalizer.normalize(NormalizationInput(original_name=variation))

    # Canonicalize
    canon_input = CanonicalizationInput(
        normalized_name=normalized.normalized,
        entity_type=EntityType.PESSOA,
        classification_confidence=0.90
    )
    result = canonicalizer.canonicalize(canon_input)
    canonical_entities.append(result.entity.canonical_name)

# All should map to same canonical name
unique_canonical = set(canonical_entities)
assert len(unique_canonical) == 1, f"Expected 1 canonical name, got {len(unique_canonical)}: {unique_canonical}"
print(f"✅ Scenario 2 - Variation Grouping: All variations mapped to '{unique_canonical.pop()}'")
```

---

### Scenario 3: GrupoPessoas Classification
**Given**: "Pesquisas da Biodiversidade"
**Expected**: Classification as `GrupoPessoas`

```python
result = classifier.classify(ClassificationInput(text="Pesquisas da Biodiversidade"))

assert result.category == "GrupoPessoas", f"Expected GrupoPessoas, got {result.category}"
assert result.confidence >= 0.70, f"Expected confidence ≥0.70, got {result.confidence}"
print(f"✅ Scenario 3 - GrupoPessoas: '{result.original_text}' → {result.category} (confidence: {result.confidence:.2f})")
```

---

### Scenario 4: Empresa/Instituição Classification
**Given**: "EMBRAPA" or "USP"
**Expected**: Classification as `Empresa`

```python
for institution in ["EMBRAPA", "USP"]:
    result = classifier.classify(ClassificationInput(text=institution))
    assert result.category == "Empresa", f"Expected Empresa for '{institution}', got {result.category}"
    print(f"✅ Scenario 4 - Empresa: '{institution}' → {result.category} (confidence: {result.confidence:.2f})")
```

---

### Scenario 5: NãoDeterminado Classification
**Given**: "?" or "sem coletor"
**Expected**: Classification as `NaoDeterminado`

```python
for unknown in ["?", "sem coletor"]:
    result = classifier.classify(ClassificationInput(text=unknown))
    assert result.category == "NaoDeterminado", f"Expected NaoDeterminado for '{unknown}', got {result.category}"
    print(f"✅ Scenario 5 - NãoDeterminado: '{unknown}' → {result.category}")
```

---

### Scenario 6: Dynamic Database Updates During Processing
**Given**: Processing 4.6M records
**Expected**: Local database updated incrementally

```python
from src.storage.local_db import LocalDatabase
from src.cli import run_pipeline  # Main pipeline orchestrator

# Initialize database
db = LocalDatabase(config_path="config.yaml")

# Get initial entity count
initial_count = len(db.get_all_entities())

# Process batch of records (simulate incremental processing)
# In real scenario, this would be 4.6M records from MongoDB
run_pipeline(batch_size=1000, max_records=10000)  # Process 10K records

# Verify database was updated
final_count = len(db.get_all_entities())
assert final_count > initial_count, f"Expected entity count to increase (was {initial_count}, now {final_count})"
print(f"✅ Scenario 6 - Dynamic Updates: Database grew from {initial_count} to {final_count} entities")
```

---

### Scenario 7: CSV Report Generation
**Given**: Processing complete
**Expected**: CSV with canonical_name, variations, occurrence_counts (3 columns, NO confidence scores)

```python
import pandas as pd

# Export to CSV
db.export_to_csv("output/canonical_report.csv")

# Validate CSV format
df = pd.read_csv("output/canonical_report.csv")

# Check columns
expected_columns = ["canonical_name", "variations", "occurrence_counts"]
assert list(df.columns) == expected_columns, f"Expected columns {expected_columns}, got {list(df.columns)}"

# Check no confidence columns exist
assert "confidence" not in df.columns, "CSV should NOT include confidence scores (per FR-025)"

# Validate data format
sample_row = df.iloc[0]
assert ";" in sample_row["variations"], "Variations should be semicolon-separated"
assert ";" in sample_row["occurrence_counts"], "Counts should be semicolon-separated"

# Verify counts align with variations
variations_count = len(sample_row["variations"].split(";"))
counts_count = len(sample_row["occurrence_counts"].split(";"))
assert variations_count == counts_count, f"Variation count ({variations_count}) must match counts ({counts_count})"

print(f"✅ Scenario 7 - CSV Export: Valid format with {len(df)} canonical entities")
print(f"   Sample row: {sample_row['canonical_name']} → {variations_count} variations")
```

---

## Performance Validation

### Target: 4.6M records in ≤6 hours (≥213 records/sec)

```python
import time
from src.cli import run_pipeline

# Benchmark processing rate
start_time = time.time()
result = run_pipeline(batch_size=10000, max_records=100000)  # Process 100K records
elapsed = time.time() - start_time

records_per_second = 100000 / elapsed
print(f"Processing rate: {records_per_second:.1f} records/sec")

# Validate meets target
assert records_per_second >= 213, f"Expected ≥213 rec/sec, got {records_per_second:.1f}"

# Estimate full 4.6M time
estimated_hours = (4_600_000 / records_per_second) / 3600
print(f"✅ Performance: {records_per_second:.1f} rec/sec → Estimated {estimated_hours:.1f}h for 4.6M records")
assert estimated_hours <= 6.0, f"Estimated time {estimated_hours:.1f}h exceeds 6-hour target"
```

---

## Integration Test: Full Pipeline E2E

```python
from src.cli import run_pipeline

# Run complete pipeline on test dataset
result = run_pipeline(
    config_path="config.yaml",
    batch_size=10000,
    workers=8,
    output_csv="output/test_report.csv"
)

# Verify all stages completed
assert result.classification_complete, "Classification stage failed"
assert result.atomization_complete, "Atomization stage failed"
assert result.normalization_complete, "Normalization stage failed"
assert result.canonicalization_complete, "Canonicalization stage failed"

# Check output artifacts
assert os.path.exists("output/test_report.csv"), "CSV report not generated"
assert os.path.exists("data/canonical_entities.db"), "Local database not created"
assert os.path.exists("docs/rules.md"), "Rules documentation not generated"

print("✅ Integration Test: Full pipeline executed successfully")
print(f"   Processed: {result.total_records} records")
print(f"   Entities created: {result.canonical_entities_count}")
print(f"   Processing time: {result.elapsed_time_seconds:.1f}s")
```

---

## Validation Checklist

Run all scenarios and check:

- [ ] Scenario 1: ConjuntoPessoas classified (≥0.90 confidence) and atomized correctly
- [ ] Scenario 2: Name variations grouped under single canonical entity
- [ ] Scenario 3: GrupoPessoas classification works
- [ ] Scenario 4: Empresa/Instituição classification works
- [ ] Scenario 5: NãoDeterminado classification works
- [ ] Scenario 6: Database updates dynamically during processing
- [ ] Scenario 7: CSV export format correct (3 columns, no confidence)
- [ ] Performance: ≥213 records/sec processing rate
- [ ] Integration: Full pipeline E2E completes without errors
- [ ] All confidence thresholds ≥0.70 enforced
- [ ] Rules documentation (`docs/rules.md`) exists and is editable

---

## Troubleshooting

### Common Issues

**Issue**: Confidence scores below 0.70
**Solution**: Check pattern matching rules in `src/pipeline/classifier.py`, adjust regex patterns

**Issue**: Variations not grouping correctly
**Solution**: Tune similarity algorithm weights in `config.yaml` → `algorithms.similarity_weights`

**Issue**: Performance below 213 rec/sec
**Solution**: Increase worker count in `config.yaml` → `processing.workers` (default 8)

**Issue**: CSV export missing data
**Solution**: Verify local database has entities: `SELECT COUNT(*) FROM canonical_entities`

---

## Success Criteria

✅ **All 7 acceptance scenarios pass**
✅ **Performance target met (≥213 rec/sec)**
✅ **Full E2E pipeline completes without errors**
✅ **Output artifacts generated (CSV, local DB, rules doc)**
✅ **All confidence thresholds enforced (≥0.70)**

**Next Steps**: Run `/tasks` to generate implementation task list.
