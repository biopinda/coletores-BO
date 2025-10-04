# NER Fallback Implementation

## Overview

The Plant Collector Canonicalization System uses a two-tier classification approach combining rule-based pattern matching with AI-powered Named Entity Recognition (NER) for improved accuracy.

## Architecture

### Tier 1: Rule-Based Classification (Primary)
- **Speed**: Instant (<0.001s per text)
- **Method**: Regex patterns, keyword detection
- **Coverage**: ~90% of cases with confidence ≥0.70

### Tier 2: NER Fallback (Secondary)
- **Activation**: Automatic when confidence < 0.70
- **Speed**: 0.03s per text (GPU) or 2s per text (CPU)
- **Method**: BERT neural network for entity recognition
- **Purpose**: Boost confidence for ambiguous cases

## NER Model Details

### Model Selection
**Selected Model**: `pierreguillou/bert-base-cased-pt-lenerbr`

**Reasoning**:
- Portuguese language specialization (trained on Brazilian legal texts)
- Optimized for person name detection
- Moderate size (414 MB) balancing accuracy and performance
- Active maintenance and good community support

**Alternatives Considered**:
- `neuralmind/bert-base-portuguese-cased`: Less specialized for NER
- `pucpr/biobertpt-all`: Biomedical focus, slower inference
- `dslim/bert-base-NER`: English-only, not suitable for Portuguese collectors

### GPU Acceleration

**Requirements**:
- NVIDIA GPU with CUDA support
- CUDA 12.4+ (compatible with older versions via backward compatibility)
- 414 MB+ VRAM

**Windows Setup**:
1. Enable Long Paths (one-time registry change)
2. Install PyTorch nightly with CUDA support
3. Automatic GPU detection at runtime

**Performance Comparison**:
| Device | Inference Time | Throughput |
|--------|---------------|------------|
| CPU | 2.0s | 0.5 texts/sec |
| GPU (GTX 1060) | 0.03s | 33 texts/sec |
| **Speedup** | **66x faster** | - |

### Entity Types Detected

| Label | Description | Action |
|-------|-------------|--------|
| PESSOA / PER | Person name | Classify as `Pessoa`, boost confidence +0.15 |
| ORGANIZACAO / ORG | Organization | Classify as `Empresa`, boost confidence +0.05 |
| Other | Location, etc. | No action, maintain original classification |

## Implementation Details

### Code Structure

**`src/pipeline/ner_fallback.py`**:
- `NERFallback` class: Main NER inference engine
- `NEREntity`: Entity data structure
- `NEROutput`: Fallback result container
- Lazy model loading (loads only on first use)
- Automatic device detection (CUDA vs CPU)

**`src/pipeline/classifier.py`**:
- Enhanced `Classifier` with optional NER integration
- `_apply_ner_fallback()`: Private method for low-confidence cases
- `ner_fallback_count`: Metric tracking

### Confidence Boost Logic

```python
def calculate_confidence_boost(ner_entities):
    if person_entity with score > 0.85:
        return +0.15
    elif person_entity with score > 0.70:
        return +0.10
    elif person_entity with score > 0.50:
        return +0.05
    elif organization_entity:
        return +0.05
    else:
        return -0.05  # penalty for no entities
```

**Maximum Confidence**: Capped at 0.95 to maintain uncertainty margin

### Memory Management

**Model Caching**:
- Model loaded once per classifier instance
- Shared across all NER calls in same pipeline run
- Hugging Face cache: `~/.cache/huggingface/hub/`

**GPU Memory**:
- Model: 414 MB
- Inference overhead: ~8 MB per batch
- Total: ~423 MB peak usage

## Usage Examples

### Basic Usage
```python
from src.pipeline.classifier import Classifier

# Initialize with NER enabled (default)
classifier = Classifier(use_ner_fallback=True, ner_device=None)

# Classify - NER triggers automatically if needed
result = classifier.classify(ClassificationInput(text="Silva J"))

print(f"Confidence: {result.confidence}")
print(f"NER used: {classifier.ner_fallback_count} times")
```

### Disable NER (CPU-only environments)
```python
# Disable NER for faster processing on CPU
classifier = Classifier(use_ner_fallback=False)
```

### Force CPU Mode
```python
# Use CPU even if GPU is available
classifier = Classifier(use_ner_fallback=True, ner_device='cpu')
```

## Performance Metrics

### Test Results (1000 records)

| Metric | Value |
|--------|-------|
| Total records | 1000 |
| Rule-based matches | 1000 (100%) |
| NER fallback triggered | 0 (0%) |
| Average confidence | 0.85 |
| Processing rate | 11.5 rec/sec |

**Note**: Current rule-based classifier achieves 0.70+ confidence on all test cases. NER fallback is ready for production edge cases.

### Expected Production Performance

Assuming 5% of 4.6M records trigger NER fallback:

**Without GPU** (CPU-only):
- NER cases: 230,000 × 2s = 460,000s (~128 hours)
- Regular cases: 4,370,000 × 0.01s = 43,700s (~12 hours)
- **Total: ~140 hours**

**With GPU** (GTX 1060):
- NER cases: 230,000 × 0.03s = 6,900s (~2 hours)
- Regular cases: 4,370,000 × 0.01s = 43,700s (~12 hours)
- **Total: ~14 hours**

**GPU Benefit**: 10x faster overall processing

## Troubleshooting

### Windows Path Length Error
**Error**: `FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\...\\torch\\include\\...'`

**Solution**:
```powershell
# Run as Administrator
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -Value 1
```

### CUDA Out of Memory
**Error**: `RuntimeError: CUDA out of memory`

**Solutions**:
1. Reduce batch size in config
2. Close other GPU applications
3. Fall back to CPU mode: `ner_device='cpu'`

### Model Download Timeout
**Error**: `HTTPError: 504 Gateway Timeout`

**Solution**:
1. Check internet connection
2. Use mirror: `export HF_ENDPOINT=https://hf-mirror.com`
3. Pre-download model: `huggingface-cli download pierreguillou/bert-base-cased-pt-lenerbr`

## Future Enhancements

### Potential Improvements
1. **Fine-tuning**: Train model specifically on plant collector names
2. **Batch Inference**: Process multiple texts simultaneously for better GPU utilization
3. **Model Quantization**: Reduce memory footprint with INT8 quantization
4. **Alternative Models**: Evaluate newer Portuguese BERT variants

### Monitoring
Track these metrics in production:
- NER fallback trigger rate
- Average confidence boost
- GPU memory usage
- Inference latency (p50, p95, p99)

## References

- Model: [pierreguillou/bert-base-cased-pt-lenerbr](https://huggingface.co/pierreguillou/bert-base-cased-pt-lenerbr)
- Dataset: [LeNER-Br](https://cic.unb.br/~teodecampos/LeNER-Br/) (Brazilian legal NER)
- PyTorch CUDA: [pytorch.org/get-started](https://pytorch.org/get-started/locally/)
- Transformers: [huggingface.co/docs/transformers](https://huggingface.co/docs/transformers)
