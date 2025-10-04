# Plant Collector Identification and Canonicalization System

NLP pipeline for identifying, classifying, and canonicalizing plant collector names from 4.6 million MongoDB records. Processes strings through classification (5 categories), atomization (name separation), normalization (standardization), and canonicalization (grouping by similarity).

## Features

- **Multi-stage NLP Pipeline**: Classification → Atomization → Normalization → Canonicalization
- **AI-Powered Classification**: Rule-based classifier with BERT NER fallback for low-confidence cases
- **GPU Acceleration**: CUDA-enabled NER model for 10-20x faster processing on NVIDIA GPUs
- **5 Classification Categories**: Pessoa, ConjuntoPessoas, GrupoPessoas, Empresa, NãoDeterminado
- **Advanced Similarity Matching**: Levenshtein (0.4) + Jaro-Winkler (0.4) + Phonetic (0.2) algorithms
- **High Performance**: Target ≥213 rec/sec (6-hour processing for 4.6M records)
- **Confidence Thresholding**: All scores ≥0.70, with NER fallback for improvement
- **CSV Export**: canonicalName, variations, occurrenceCounts (no confidence scores)

## Installation

**Requirements**: Python 3.11+

### Standard Installation (CPU only)

```bash
pip install -r requirements-minimal.txt
```

### GPU-Accelerated Installation (Recommended)

For NVIDIA GPUs with CUDA support:

1. **Enable Windows Long Paths** (Windows only, one-time setup):
   ```powershell
   # Run as Administrator
   Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -Value 1
   ```

2. **Install PyTorch with CUDA** (for Python 3.13):
   ```bash
   pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu124
   ```

3. **Install remaining dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

**GPU Benefits**: 10-20x faster NER inference (0.03s vs 0.5s per text)

## Configuration

Edit `config.yaml`:

```yaml
mongodb:
  uri: "mongodb://localhost:27017"
  database: "dwc2json"
  collection: "ocorrencias"
  filter: { kingdom: "Plantae" }

local_db:
  type: "duckdb"
  path: "./data/canonicalEntities.db"

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

## Usage

Run the pipeline:

```bash
python src/cli.py --config config.yaml
```

Process limited records (for testing):

```bash
python src/cli.py --config config.yaml --max-records 1000
```

## Testing

Run all tests:

```bash
pytest tests/
```

Run specific test suites:

```bash
# Contract tests (schema validation)
pytest tests/contract/

# Integration tests (acceptance scenarios)
pytest tests/integration/

# Unit tests (individual components)
pytest tests/unit/
```

## Project Structure

```
src/
├── pipeline/          # Processing stages
│   ├── classifier.py     # Classification (5 categories) with NER fallback
│   ├── ner_fallback.py   # BERT NER model for low-confidence cases
│   ├── atomizer.py       # Name separation
│   ├── normalizer.py     # Standardization
│   └── canonicalizer.py  # Similarity grouping
├── algorithms/        # Similarity and phonetic algorithms
├── models/            # Pydantic data models
├── storage/           # MongoDB source + DuckDB local DB
├── cli.py             # Main CLI entry point
└── config.py          # Configuration management

tests/
├── contract/          # Schema validation tests
├── integration/       # Acceptance scenario tests
└── unit/              # Component unit tests
```

## Performance

- **Target**: ≥213 records/second
- **Expected Runtime**: ~6 hours for 4.6M records
- **Batch Processing**: Configurable worker count (default: 8)
- **Memory Efficient**: Streaming cursors, incremental DB updates

## Output

**CSV Format** (`output/canonical_report.csv`):

| canonicalName | variations | occurrenceCounts |
|---------------|------------|------------------|
| FORZZA, R.C. | FORZZA, R.C.;R.C. FORZZA;RAFAELA C. FORZZA | 1523;847;234 |
| SILVA, J. | SILVA, J.;J. SILVA | 2891;1205 |

**Local Database**: DuckDB at `data/canonicalEntities.db` with canonical entities and variations

## NER Fallback (AI Classification)

The system uses a two-stage classification approach:

1. **Rule-Based Classification** (Fast, Pattern Matching)
   - Regex patterns for name formats
   - Keyword detection for organizations/groups
   - Confidence scores based on pattern strength

2. **NER Fallback** (AI-Powered, GPU-Accelerated)
   - **Trigger**: Automatically activates when confidence < 0.70
   - **Model**: `pierreguillou/bert-base-cased-pt-lenerbr` (Portuguese BERT)
   - **GPU Usage**: 414 MB VRAM, 0.03s inference per text
   - **Confidence Boost**: +0.05 to +0.15 based on entity detection
   - **Entity Types**: PESSOA (person), ORGANIZACAO (organization)

**Performance Impact**:
- CPU-only: ~2s per low-confidence case
- GPU-accelerated: ~0.03s per low-confidence case (60x faster)

**Usage Tracking**: Pipeline reports total NER fallback calls in summary

## Algorithm Documentation

Classification patterns, normalization rules, and similarity algorithms are documented in `docs/rules.md` (editable for algorithm refinement).

## Development

**Code Quality**:
```bash
# Type checking
mypy src/

# Linting
ruff check src/

# Formatting
black src/
```

**Test Coverage**:
```bash
pytest --cov=src --cov-report=term-missing
```

---

Generated with ✨ Claude Code
