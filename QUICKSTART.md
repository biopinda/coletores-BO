# Quick Start Guide

## Installation Options

### Option 1: Minimal Install (Recommended - No NER)

This installs all core functionality without the NER fallback feature:

```bash
pip install -r requirements-minimal.txt
```

**Use this if:**
- You're getting torch installation errors (Windows path length issues)
- You don't need NER fallback for low-confidence classifications
- You want to start testing the pipeline immediately

### Option 2: Full Install (With NER Support)

For NER fallback support, install in two steps:

**Step 1: Install core dependencies**
```bash
pip install -r requirements-minimal.txt
```

**Step 2: Install PyTorch CPU version (avoids path length issues)**
```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install transformers>=4.35.0
```

## Configuration

Edit `config.yaml` to point to your MongoDB:

```yaml
mongodb:
  uri: "mongodb://username:password@host:port/?authSource=admin"
  database: "your_database"
  collection: "your_collection"
  filter: { kingdom: "Plantae" }
```

## Run Tests

Verify installation:

```bash
# All contract tests should pass (49 tests)
pytest tests/contract/ -v

# Quick smoke test
python src/cli.py --config config.yaml --max-records 10
```

## Run Pipeline

**Test run (100 records):**
```bash
python src/cli.py --config config.yaml --max-records 100
```

**Full pipeline:**
```bash
python src/cli.py --config config.yaml
```

## Troubleshooting

### Error: torch installation fails

**Solution:** Use minimal install (without NER):
```bash
pip install -r requirements-minimal.txt
```

The pipeline works perfectly without NER. NER is only used as a fallback for classifications with confidence <0.70.

### Error: MongoDB connection refused

**Solution:** Check your MongoDB URI in `config.yaml` and ensure MongoDB is running.

### Error: Module not found

**Solution:** Make sure you're in the project root directory:
```bash
cd /path/to/coletoresBO
python src/cli.py --config config.yaml
```

## Expected Output

After running the pipeline, you'll see:

1. **Progress bar** showing records/sec
2. **CSV file** at `output/canonical_report.csv`
3. **DuckDB database** at `data/canonicalEntities.db`

**CSV Format:**
```
canonicalName,variations,occurrenceCounts
SILVA, J.,SILVA, J.;J. SILVA,150;75
FORZZA, R.C.,FORZZA, R.C.;R.C. FORZZA,1200;300
```

## Next Steps

1. ✅ Verify tests pass: `pytest tests/contract/`
2. ✅ Test with small dataset: `--max-records 100`
3. ✅ Check CSV output format
4. ✅ Run full pipeline on production data
5. ✅ Review `docs/rules.md` for algorithm tuning

---

**Need Help?** Check `IMPLEMENTATION_SUMMARY.md` for detailed architecture info.
