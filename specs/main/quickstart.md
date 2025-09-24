# Quickstart Guide: Sistema de Canonicalização de Coletores Biológicos

**Version**: 1.0.0
**Date**: 2025-09-24
**Prerequisites**: Python 3.11+, MongoDB 4.4+, 8GB+ RAM

## Overview

This quickstart guide demonstrates the collector canonicalization system by processing a sample of biological specimen records and generating canonical collector identities. The system classifies collector strings into 6 entity types and groups variations using similarity scoring.

## Quick Start (5 minutes)

### 1. Environment Setup

```bash
# Clone repository
git clone https://github.com/biopinda/coletores-BO.git
cd coletores-BO

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. MongoDB Connection

```bash
# Set MongoDB connection string
export MONGODB_CONNECTION_STRING="mongodb://localhost:27017"
# Or create .env file with:
echo "MONGODB_CONNECTION_STRING=mongodb://localhost:27017" > .env
```

### 3. Run Sample Canonicalization

```bash
# Process sample dataset (1,000 records)
python -m src.cli canonicalize \
  --database dwc2json \
  --batch-size 1000 \
  --sample-size 1000 \
  --output-dir ./quickstart-output

# Expected output:
# ✓ Processed 1,000 records in 45 seconds
# ✓ Created 234 canonical collectors
# ✓ Generated reports in ./quickstart-output/
```

## Step-by-Step Tutorial

### Step 1: Data Preparation

```python
# Verify your MongoDB collection structure
from src.mongodb_manager import GerenciadorMongoDB

mongo = GerenciadorMongoDB()
sample_records = list(mongo.ocorrencias.find(
    {"recordedBy": {"$exists": True, "$ne": None}},
    {"recordedBy": 1, "kingdom": 1}
).limit(5))

print("Sample records:")
for record in sample_records:
    print(f"- {record['recordedBy']} ({record.get('kingdom', 'Unknown')})")
```

Expected output:
```
Sample records:
- Silva, J. & R.C. Forzza (Plantae)
- Santos, M. et al. (Animalia)
- Herbário RB (Plantae)
- ? (Plantae)
- João (Animalia)
```

### Step 2: Classification Test

```python
# Test collector classification
from src.canonicalizador_coletores import CanonizalizadorColetores

canonizer = CanonizalizadorColetores()

# Test different collector types
test_collectors = [
    "Silva, J. & R.C. Forzza",          # conjunto_pessoas
    "Santos, Maria José",                # pessoa
    "Herbário RB",                      # empresa_instituicao
    "Silva et al.",                     # grupo_pessoas
    "?",                                # coletor_indeterminado
    "João"                              # representacao_insuficiente
]

for collector in test_collectors:
    result = canonizer.classificar_entidade(collector)
    print(f"{collector:30} → {result.entity_type} ({result.confidence_score:.2f})")
```

Expected output:
```
Silva, J. & R.C. Forzza        → conjunto_pessoas (0.95)
Santos, Maria José             → pessoa (0.88)
Herbário RB                    → empresa_instituicao (0.92)
Silva et al.                   → grupo_pessoas (0.85)
?                              → coletor_indeterminado (1.00)
João                           → representacao_insuficiente (0.90)
```

### Step 3: Similarity Scoring Test

```python
# Test similarity scoring between collector names
from src.similarity_calculator import SimilarityScore

# Test similar names that should be grouped
similar_names = [
    ("Forzza, R.C.", "R.C. Forzza"),
    ("Silva, J.", "Silva, João"),
    ("Santos, M.", "Santos, Maria")
]

for name1, name2 in similar_names:
    # Normalize names first
    norm1 = canonizer._normalizar_nome_pessoa(name1)
    norm2 = canonizer._normalizar_nome_pessoa(name2)

    # Calculate similarity
    score = SimilarityScore.calculate(norm1, norm2)

    print(f"{name1} vs {name2}")
    print(f"  Composite: {score.composite_score:.3f} ({'✓' if score.threshold_met else '✗'})")
    print(f"  Surname: {score.surname_similarity:.3f}, Initial: {score.initial_compatibility:.3f}, Phonetic: {score.phonetic_similarity:.3f}")
    print()
```

Expected output:
```
Forzza, R.C. vs R.C. Forzza
  Composite: 0.920 (✓)
  Surname: 1.000, Initial: 1.000, Phonetic: 1.000

Silva, J. vs Silva, João
  Composite: 0.856 (✓)
  Surname: 1.000, Initial: 0.750, Phonetic: 1.000

Santos, M. vs Santos, Maria
  Composite: 0.865 (✓)
  Surname: 1.000, Initial: 0.800, Phonetic: 1.000
```

### Step 4: Full Canonicalization

```python
# Run complete canonicalization process
from src.processar_coletores import main as processar_main
import sys

# Configure for quickstart
sys.argv = [
    'processar_coletores.py',
    '--batch-size', '1000',
    '--max-records', '5000',  # Process only 5k records for demo
    '--output-reports',
    '--checkpoint-interval', '1000'
]

# Run canonicalization
result = processar_main()

print(f"Processing completed!")
print(f"Records processed: {result['records_processed']}")
print(f"Canonical collectors: {result['canonical_collectors_created']}")
print(f"Processing time: {result['processing_time']:.1f}s")
```

### Step 5: Examine Results

```python
# Examine created canonical collectors
mongo = GerenciadorMongoDB()

# Get top collectors by frequency
top_collectors = list(mongo.coletores.find(
    {"tipo_entidade": {"$in": ["pessoa", "conjunto_pessoas"]}},
    {"forma_canonica": 1, "total_ocorrencias": 1, "estatisticas_reino": 1}
).sort("total_ocorrencias", -1).limit(10))

print("Top 10 Canonical Collectors:")
print("-" * 60)
for collector in top_collectors:
    reino_stats = collector.get('estatisticas_reino', {})
    plantae = reino_stats.get('Plantae', {}).get('contagem_coletas', 0)
    animalia = reino_stats.get('Animalia', {}).get('contagem_coletas', 0)

    print(f"{collector['forma_canonica']:25} | {collector['total_ocorrencias']:4d} | P:{plantae:3d} A:{animalia:3d}")
```

Expected output:
```
Top 10 Canonical Collectors:
------------------------------------------------------------
Silva, R.C.              |  234 | P:180 A: 54
Santos, M.J.             |  198 | P: 45 A:153
Herbário RB              |  156 | P:156 A:  0
Forzza, R.C.             |  134 | P:134 A:  0
Lima, H.C.               |  98  | P: 98 A:  0
```

## Validation Tests

### Test 1: Classification Accuracy
```python
# Verify all 6 entity types are detected
entity_counts = mongo.db.classifications.aggregate([
    {"$group": {"_id": "$entity_type", "count": {"$sum": 1}}}
])

print("Entity Type Distribution:")
for result in entity_counts:
    print(f"  {result['_id']:25}: {result['count']:4d} records")

# Should show all 6 types: pessoa, conjunto_pessoas, grupo_pessoas,
# empresa_instituicao, coletor_indeterminado, representacao_insuficiente
```

### Test 2: Similarity Grouping
```python
# Check that similar variations are properly grouped
sample_canonical = mongo.coletores.find_one(
    {"forma_canonica": {"$regex": "Silva"}},
    {"forma_canonica": 1, "variacoes": 1}
)

if sample_canonical:
    print(f"Canonical: {sample_canonical['forma_canonica']}")
    print("Variations grouped:")
    for variation in sample_canonical['variacoes'][:5]:  # Show first 5
        print(f"  - {variation['texto_original']} (freq: {variation['contagem_frequencia']})")
```

### Test 3: Checkpoint Recovery
```python
# Test checkpoint functionality
print("Testing checkpoint recovery...")

# Save current state
checkpoint = {
    "tipo": "quickstart_test",
    "last_processed_id": "test_checkpoint",
    "records_processed": 1000,
    "timestamp": datetime.now()
}

mongo.salvar_checkpoint(checkpoint)

# Load checkpoint
loaded = mongo.carregar_checkpoint("quickstart_test")
if loaded:
    print(f"✓ Checkpoint saved and loaded successfully")
    print(f"  Records processed: {loaded['records_processed']}")
else:
    print("✗ Checkpoint test failed")
```

## Expected Results

After running the quickstart, you should have:

### Generated Files
```
quickstart-output/
├── relatorio_canonicalizacao.txt       # Main canonicalization report
├── top_coletores.txt                    # Top collectors by frequency
├── estatisticas_processamento.json     # Processing statistics
├── validacao_qualidade.txt             # Quality validation results
└── logs/
    └── canonicalizacao_YYYYMMDD.log    # Processing logs
```

### Database Collections
```javascript
// New collections created:
db.classifications.count()        // ~5,000 classification results
db.checkpoints.count()           // 1-5 checkpoint documents

// Updated collections:
db.coletores.count()             // ~500-1000 canonical collectors
```

### Performance Metrics
- **Processing Speed**: ~100-150 records/second
- **Memory Usage**: <200MB peak
- **Accuracy**: >95% classification accuracy
- **Grouping**: ~85% of variations correctly grouped

## Troubleshooting

### Common Issues

**Issue**: `pymongo.errors.ServerSelectionTimeoutError`
```bash
# Solution: Check MongoDB connection
mongosh --eval "db.runCommand('ping')"
# Or update connection string in config
```

**Issue**: `MemoryError during processing`
```bash
# Solution: Reduce batch size
python -m src.cli canonicalize --batch-size 1000
```

**Issue**: `No records found with recordedBy field`
```bash
# Solution: Check collection name and field names
python -c "
from src.mongodb_manager import GerenciadorMongoDB
mongo = GerenciadorMongoDB()
print('Collections:', mongo.db.list_collection_names())
sample = mongo.ocorrencias.find_one()
print('Sample fields:', list(sample.keys()) if sample else 'No documents')
"
```

### Performance Tuning

For larger datasets, adjust these parameters:

```python
# In config/algorithm_config.py
ALGORITHM_CONFIG = {
    'batch_size': 5000,           # Increase for better throughput
    'checkpoint_interval': 25000,  # Increase for fewer checkpoints
    'similarity_threshold': 0.85,  # Adjust grouping sensitivity
    'parallel_batches': True,      # Enable parallel processing
}

# In config/mongodb_config.py
MONGODB_CONFIG = {
    'max_pool_size': 50,          # More connections for throughput
    'timeout': 30000,             # Longer timeout for large operations
}
```

## Next Steps

1. **Scale Testing**: Process larger datasets (100k-1M records)
2. **Custom Configuration**: Adjust similarity thresholds for your data
3. **Quality Validation**: Review and approve canonical assignments
4. **Report Analysis**: Analyze collector specialization patterns
5. **Integration**: Integrate with existing biodiversity workflows

## Support

- **Documentation**: See `/docs/` directory for detailed guides
- **Configuration**: Review `/config/` files for customization options
- **Logs**: Check `/logs/` directory for detailed processing information
- **Issues**: Report problems at [GitHub Issues](https://github.com/biopinda/coletores-BO/issues)

## Validation Checklist

- [ ] MongoDB connection successful
- [ ] Sample records processed without errors
- [ ] All 6 entity types detected in results
- [ ] Canonical collectors created with variations
- [ ] Similarity scores within expected ranges (0.85+ for grouping)
- [ ] Reports generated in output directory
- [ ] Checkpoint save/load functionality working
- [ ] Memory usage under 500MB during processing
- [ ] Processing speed >50 records/second