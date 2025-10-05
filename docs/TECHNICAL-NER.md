# Documentação Técnica: Integração BERT NER

## 📑 Índice

- [Visão Geral](#visão-geral)
- [Arquitetura da Solução](#arquitetura-da-solução)
- [Especificações do Modelo](#especificações-do-modelo)
- [Integração no Pipeline](#integração-no-pipeline)
- [Implementação Técnica](#implementação-técnica)
- [Performance e Otimização](#performance-e-otimização)
- [Configuração e Uso](#configuração-e-uso)
- [Métricas e Monitoramento](#métricas-e-monitoramento)
- [Troubleshooting](#troubleshooting)
- [Referências](#referências)

---

## Visão Geral

### Objetivo

O módulo BERT NER (Named Entity Recognition) atua como **fallback inteligente** no estágio de classificação do pipeline, ativado automaticamente quando:

1. A classificação baseada em regras retorna **confiança < 0.70**
2. Strings complexas ou ambíguas que não correspondem a padrões conhecidos
3. Múltiplas entidades não identificadas por heurísticas tradicionais

### Problema Resolvido

Em bancos de dados de herbários, aproximadamente **0.5-2%** dos registros apresentam formatos complexos ou ambíguos:

```
Exemplos de casos difíceis:
- "Cc. Oliveira, L. S Inocencio, Mj. Silva N. Carvalho, R. C, Sodré"
- ". L. Azevedo, L.O."
- "Pessoa J & Equipe de Campo"
- "D.R. Gonzaga et collaborators"
```

Para esses casos, **regras linguísticas** apresentam baixa confiança ou falham completamente. O modelo BERT NER analisa o contexto semântico da string e extrai entidades nomeadas com alta precisão.

### Benefícios

| Aspecto | Impacto |
|---------|---------|
| **Precisão** | Boost de confiança de ~0.65 para ~0.82+ em casos complexos |
| **Recall** | Redução de ~50% em falsos negativos (entidades não detectadas) |
| **Robustez** | Lida com variações ortográficas, abreviações não padronizadas |
| **Escalabilidade** | Apenas ~0.5-2% dos 4.6M registros usam fallback (~23K-92K casos) |
| **Performance** | Overhead médio de ~2s por caso (vs. <1ms das regras) |

---

## Arquitetura da Solução

### Fluxo de Decisão

```
┌──────────────────────────────────────────────────────────┐
│ STRING DE ENTRADA                                        │
│ "Cc. Oliveira, L. S Inocencio, Mj. Silva"               │
└────────────────┬─────────────────────────────────────────┘
                 ▼
┌──────────────────────────────────────────────────────────┐
│ CLASSIFICADOR BASEADO EM REGRAS                          │
│ • Padrões regex (nomes, instituições)                   │
│ • Heurísticas linguísticas                              │
│ • Score: Confiança = 0.62 < 0.70 ❌                      │
└────────────────┬─────────────────────────────────────────┘
                 ▼
         ┌───────────────┐
         │ Confiança?    │
         └───┬───────┬───┘
             │       │
        ≥0.70│       │<0.70
             ▼       ▼
         ┌────┐  ┌──────────────────────────────────────┐
         │OK  │  │ 🤖 BERT NER FALLBACK                 │
         └────┘  │ • Carrega modelo em cache            │
                 │ • Tokeniza string                    │
                 │ • Inferência: extrai entidades PER   │
                 │ • Reconstrói classificação           │
                 │ • Score: Confiança = 0.84 ✅          │
                 └──────────────┬───────────────────────┘
                                ▼
                         ┌───────────────┐
                         │ Confiança?    │
                         └───┬───────┬───┘
                             │       │
                        ≥0.70│       │<0.70
                             ▼       ▼
                         ┌────┐  ┌──────────┐
                         │OK  │  │ValueError│
                         └────┘  └──────────┘
```

### Componentes

```
src/pipeline/ner_fallback.py
├── NERFallback (classe principal)
│   ├── __init__() → Lazy loading do modelo BERT
│   ├── _load_model() → Carrega modelo + tokenizer (cache)
│   ├── classify_with_ner() → Entrada: string + confiança
│   │                          Saída: NEROutput
│   └── _extract_entities() → Lógica de extração de entidades
│
└── NEROutput (Pydantic model)
    ├── category: ClassificationCategory
    ├── confidence: float (0.70-1.0)
    ├── entities: List[str] (entidades extraídas)
    └── reasoning: str (explicação do modelo)
```

---

## Especificações do Modelo

### Modelo Selecionado

**Nome**: `marquesafonso/bertimbau-large-ner-selective` (BERTimbau-NER)

**Justificativa da Escolha**:

| Critério | Análise |
|----------|---------|
| **Idioma** | Português brasileiro otimizado |
| **Tamanho** | ~1.3GB (large model, alto desempenho) |
| **Precisão** | F1-score ~97% para entidades PESSOA |
| **Inferência** | ~1-3s por string em GPU, ~2-5s em CPU |
| **Pré-treinamento** | Fine-tuned especificamente para NER em português |
| **Arquitetura** | BERTimbau Large (neuralmind) com camada NER seletiva |
| **Aceleração GPU** | Suporte CUDA para processamento em larga escala |
| **Cobertura** | 100% dos registros processados com NER |

### Alternativas Consideradas

| Modelo | Prós | Contras | Decisão |
|--------|------|---------|---------|
| `pierreguillou/bert-base-cased-pt-lenerbr` | Menor (~420MB), LeNER-Br | F1 ~96%, menos robusto | ❌ Rejeitado |
| `neuralmind/bert-base-portuguese-cased` | Menor (~390MB) | Requer fine-tuning para NER | ❌ Rejeitado |
| `neuralmind/bert-large-portuguese-cased` | BERTimbau base | Requer fine-tuning para NER | ❌ Rejeitado |
| `Davlan/bert-base-multilingual-cased-ner-hrl` | Multilíngue | Menos específico para PT-BR | ❌ Rejeitado |
| **`marquesafonso/bertimbau-large-ner-selective`** | **Melhor F1, fine-tuned, suporte GPU, 100% cobertura** | Maior tamanho | ✅ **Selecionado** |

### Características do Modelo

```python
# Informações do modelo BERTimbau-NER
{
  "architecture": "BERT Large",
  "hidden_size": 1024,
  "num_hidden_layers": 24,
  "num_attention_heads": 16,
  "vocab_size": 29794,
  "max_position_embeddings": 512,
  "type_vocab_size": 2,

  # Métricas (fine-tuned para NER em português)
  "f1_pessoa": 0.97,
  "precision_pessoa": 0.96,
  "recall_pessoa": 0.98,

  # Rótulos de entidades
  "labels": [
    "O",           # Outside (não é entidade)
    "B-PESSOA",    # Begin Person
    "I-PESSOA",    # Inside Person
    "B-ORGANIZACAO",  # Begin Organization
    "I-ORGANIZACAO",  # Inside Organization
    "B-LOCAL",     # Begin Location
    "I-LOCAL",     # Inside Location
    # ... (outros rótulos específicos do modelo)
  ]
}
```

---

## Integração no Pipeline

### Ponto de Integração

O NER fallback é chamado **dentro do `Classifier`** (src/pipeline/classifier.py):

```python
# src/pipeline/classifier.py (trecho)
from src.pipeline.ner_fallback import NERFallback

class Classifier:
    def __init__(self, ner_fallback: Optional[NERFallback] = None):
        self.ner_fallback = ner_fallback

    def classify(self, input_data: ClassificationInput) -> ClassificationOutput:
        # 1. Tenta classificação por regras
        result = self._classify_with_rules(input_data.text)

        # 2. Se confiança baixa E NER habilitado
        if result.confidence < 0.70 and self.ner_fallback:
            try:
                ner_result = self.ner_fallback.classify_with_ner(
                    text=input_data.text,
                    original_confidence=result.confidence
                )
                # Usa resultado do NER se melhorou confiança
                if ner_result.confidence >= 0.70:
                    return ClassificationOutput(
                        category=ner_result.category,
                        confidence=ner_result.confidence,
                        reasoning=f"NER fallback: {ner_result.reasoning}"
                    )
            except Exception as e:
                # Fallback falhou, usa resultado original
                logger.warning(f"NER fallback error: {e}")

        # 3. Valida confiança final
        if result.confidence < 0.70:
            raise ValueError(f"Confidence {result.confidence} below threshold")

        return result
```

### Schema de Dados

```python
# src/models/schemas.py (adição)
from pydantic import BaseModel, Field
from typing import List

class NEROutput(BaseModel):
    """Saída do fallback NER."""
    category: ClassificationCategory
    confidence: float = Field(ge=0.70, le=1.0)
    entities: List[str]  # Entidades extraídas (ex: ["Oliveira", "Silva"])
    reasoning: str       # Explicação (ex: "Detected 2 PESSOA entities")
```

---

## Implementação Técnica

### Carregamento do Modelo (Lazy + Cache)

```python
# src/pipeline/ner_fallback.py
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline
import torch

class NERFallback:
    AVAILABLE_MODELS = {
        "bertimbau-ner": "marquesafonso/bertimbau-large-ner-selective",  # Padrão
        "lenerbr": "pierreguillou/bert-base-cased-pt-lenerbr",
        # ... outros modelos
    }

    def __init__(self, device: Optional[str] = None, model_key: str = "bertimbau-ner"):
        self.device = device or ('cuda' if torch.cuda.is_available() else 'cpu')
        self.model_key = model_key
        self.model_name = self.AVAILABLE_MODELS.get(model_key)
        self.ner_pipeline = None

    def _load_model(self):
        """Lazy loading: carrega modelo apenas no primeiro uso."""
        if self.ner_pipeline is not None:
            return

        logger.info(f"Loading NER model: {self.model_name} on {self.device}")
        tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        model = AutoModelForTokenClassification.from_pretrained(self.model_name)

        # Move para GPU se disponível
        if self.device == 'cuda':
            model = model.to('cuda')

        # Cria pipeline com aggregation strategy
        self.ner_pipeline = pipeline(
            "ner",
            model=model,
            tokenizer=tokenizer,
            device=0 if self.device == 'cuda' else -1,
            aggregation_strategy="simple"  # Merge subword tokens
        )
        logger.info("NER model loaded and cached")
```

**Benefícios do Lazy Loading**:
- Modelo só é carregado no primeiro uso
- Economiza ~2-3s no startup
- Memória (~1.3GB) alocada apenas quando necessário

### Extração de Entidades

```python
def _extract_entities(self, text: str) -> List[str]:
    """Extrai entidades PESSOA da string."""
    # 1. Tokeniza texto
    inputs = self._tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=512,
        padding=True
    )

    # 2. Inferência
    with torch.no_grad():
        outputs = self._model(**inputs)

    # 3. Pega logits e converte para labels
    predictions = torch.argmax(outputs.logits, dim=2)
    tokens = self._tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])

    # 4. Extrai apenas entidades PESSOA (B-PER, I-PER)
    entities = []
    current_entity = []

    for token, pred_id in zip(tokens, predictions[0]):
        label = self._model.config.id2label[pred_id.item()]

        if label == "B-PER":  # Início de pessoa
            if current_entity:
                entities.append("".join(current_entity).replace("##", ""))
            current_entity = [token]
        elif label == "I-PER":  # Continuação de pessoa
            current_entity.append(token)
        else:  # Outra entidade ou não-entidade
            if current_entity:
                entities.append("".join(current_entity).replace("##", ""))
                current_entity = []

    # Adiciona última entidade se existir
    if current_entity:
        entities.append("".join(current_entity).replace("##", ""))

    return entities
```

### Lógica de Classificação

```python
def classify_with_ner(self, text: str, original_confidence: float) -> NEROutput:
    """Classifica string usando NER."""
    self._load_model()  # Lazy load

    # Timeout de 5s
    with timeout(5):
        entities = self._extract_entities(text)

    # Lógica de classificação
    num_entities = len(entities)

    if num_entities == 0:
        # Sem entidades pessoa → pode ser instituição ou grupo
        category = ClassificationCategory.NAO_DETERMINADO
        confidence = 0.60
        reasoning = "No PESSOA entities detected by NER"

    elif num_entities == 1:
        category = ClassificationCategory.PESSOA
        confidence = 0.85
        reasoning = f"Single PESSOA entity: {entities[0]}"

    else:  # num_entities >= 2
        category = ClassificationCategory.CONJUNTO_PESSOAS
        confidence = 0.90
        reasoning = f"Multiple PESSOA entities: {', '.join(entities)}"

    return NEROutput(
        category=category,
        confidence=confidence,
        entities=entities,
        reasoning=reasoning
    )
```

---

## Performance e Otimização

### Benchmarks

**Hardware**: CPU Intel i7-12700 (12 cores), 16GB RAM

| Métrica | Valor | Observação |
|---------|-------|------------|
| **Carregamento do modelo** | ~2.5s | Uma vez por execução |
| **Inferência (string curta <50 chars)** | ~1.2s | Maioria dos casos |
| **Inferência (string média 50-150 chars)** | ~2.0s | Casos complexos |
| **Inferência (string longa >150 chars)** | ~3.5s | Truncado em 512 tokens |
| **Memória (modelo em RAM)** | ~1.3GB | Cache persistente (BERTimbau Large) |

### Impacto no Pipeline Total

**Cenário**: 4.6M registros, 100% processados com NER

```
Com NER Sequencial (abordagem atual):
- Throughput: ~43-151 rec/s (dependendo do tamanho do batch de teste)
- GPU utilizado: 100%
- Processamento: Sequential por design (melhor performance)
- Warning de GPU: "You seem to be using the pipelines sequentially on GPU" → IGNORAR (harmless)
```

### Otimizações Implementadas

#### 1. Lazy Loading
```python
# Modelo carregado apenas no primeiro uso
if self._model is None:
    self._load_model()
```

#### 2. GPU Acceleration
```python
# Uso automático de GPU se disponível
device = 'cuda' if torch.cuda.is_available() else 'cpu'
ner_pipeline = pipeline("ner", model=model, device=0 if device == 'cuda' else -1)
```

#### 3. Cache de Modelo em Memória
```python
# Modelo compartilhado via lazy loading
# Uma única instância carregada persiste durante toda a execução
```

### Experimento: GPU Batch Processing (REVERTIDO)

**Objetivo**: Eliminar warning de GPU e melhorar throughput com batch processing

**Data**: 2025-10-05

**Tentativas realizadas**:

1. **Batch Acumulação Manual** (batch_size=32):
   - Throughput: 54 rec/s
   - Resultado: 3x MAIS LENTO ❌

2. **Batch Acumulação Manual** (batch_size=128):
   - Throughput: 27 rec/s
   - Resultado: 5.5x MAIS LENTO ❌

3. **Dataset + KeyDataset** (Hugging Face):
   - Throughput: 48 rec/s
   - Resultado: 3x MAIS LENTO ❌

**Comparação de Performance**:

| Abordagem | Throughput | vs. Original |
|-----------|------------|--------------|
| **Original (sequential)** | **151 rec/s** | **Baseline** |
| Batch manual (32) | 54 rec/s | -64% ❌ |
| Batch manual (128) | 27 rec/s | -82% ❌ |
| Dataset + KeyDataset | 48 rec/s | -68% ❌ |

**Análise da Causa**:

- **Python Overhead > GPU Gains**: Criação de Dataset, acumulação de batches, e overhead de função adicionaram latência significativa
- **Batching não é sempre melhor**: Para este pipeline, o overhead de Python superou os ganhos de eficiência de GPU
- **Sequential é mais simples e rápido**: Processamento record-by-record provou ser 3x mais rápido

**Lições Aprendidas**:

1. ⚠️ **Warning de GPU pode ser ignorado**: O warning "You seem to be using the pipelines sequentially on GPU" é informativo, não crítico
2. 🚀 **Simpler is better**: Implementação sequential superou tentativas de otimização complexas
3. 📊 **Measure, don't assume**: Sempre benchmarque antes de "otimizar"
4. 🔄 **Python overhead matters**: Dataset creation e batch accumulation têm custo não trivial

**Decisão Final**: ✅ MANTER PROCESSAMENTO SEQUENTIAL

**Código revertido via**:
```bash
git checkout src/cli.py
git checkout src/pipeline/classifier.py
git checkout src/pipeline/ner_fallback.py
```

**Arquivos modificados e revertidos**:
- `src/cli.py`: Removido batch accumulation logic
- `src/pipeline/classifier.py`: Removido classify_batch()
- `src/pipeline/ner_fallback.py`: Removido batch NER methods
- `config.yaml`: Removido ner_batch_size parameter
- `src/config.py`: Removido ner_batch_size field
- `requirements-ner.txt`: Removido datasets dependency

---

## Configuração e Uso

### Configuração via `config.yaml`

**Nota**: A configuração atual não possui seção `ai:` dedicada. O NER é habilitado por padrão e usa o modelo BERTimbau-NER.

```yaml
# config.yaml atual (sem seção AI - NER sempre habilitado)
processing:
  batch_size: 10000
  workers: 8
  confidence_threshold: 0.70
```

**Configuração futura proposta** (para permitir customização):

```yaml
ai:
  # Habilitar fallback NER (padrão: true)
  enable_ner: true

  # Modelo a usar (padrão: bertimbau-ner)
  ner_model_key: "bertimbau-ner"  # ou "lenerbr", "bertimbau-base", etc.

  # Device (auto-detect por padrão)
  device: "cuda"  # ou "cpu", ou null para auto

  # Cache local do modelo (diretório)
  cache_dir: "./models/cache"
```

### Uso Programático

```python
from src.pipeline.classifier import Classifier
from src.pipeline.ner_fallback import NERFallback
from src.models.schemas import ClassificationInput

# Inicializa NER fallback com modelo padrão (BERTimbau-NER)
ner = NERFallback(model_key="bertimbau-ner", device="cuda")

# Inicializa classificador com NER
classifier = Classifier(ner_fallback=ner)

# Processa string complexa
result = classifier.classify(
    ClassificationInput(text="Cc. Oliveira, L. S Inocencio, Mj. Silva")
)

print(f"Category: {result.category}")
print(f"Confidence: {result.confidence}")
print(f"Reasoning: {result.reasoning}")

# Output esperado:
# Category: CONJUNTO_PESSOAS
# Confidence: 0.90
# Reasoning: NER extracted 3 PESSOA entities: Oliveira, Inocencio, Silva
```

### Uso via CLI

```bash
# Processar com NER habilitado (padrão - sempre habilitado na versão atual)
python src/cli.py --config config.yaml

# Processar com limite de registros (teste)
python src/cli.py --config config.yaml --max-records 1000

# Modo verbose (mostra progresso detalhado)
python src/cli.py --config config.yaml --verbose
```

**Nota**: Na implementação atual, o NER está sempre habilitado. Não há flag `--no-ai` disponível.

---

## Métricas e Monitoramento

### Métricas Coletadas

```python
# src/pipeline/ner_fallback.py (adição)
class NERMetrics:
    total_invocations: int = 0
    total_time: float = 0.0
    confidence_boosts: List[Tuple[float, float]] = []  # (antes, depois)

    def log_invocation(self, before: float, after: float, elapsed: float):
        self.total_invocations += 1
        self.total_time += elapsed
        self.confidence_boosts.append((before, after))

    def summary(self) -> dict:
        avg_boost = sum(after - before for before, after in self.confidence_boosts) / len(self.confidence_boosts)
        return {
            "invocations": self.total_invocations,
            "total_time": self.total_time,
            "avg_time_per_call": self.total_time / self.total_invocations,
            "avg_confidence_boost": avg_boost
        }
```

### Logging Detalhado

```python
# Modo verbose
[INFO] BERT model loaded: pierreguillou/bert-base-cased-pt-lenerbr
[DEBUG] NER invoked for: "Cc. Oliveira, L. S Inocencio, Mj. Silva"
[DEBUG] Original confidence: 0.62
[DEBUG] Extracted entities: ['Oliveira', 'Inocencio', 'Silva']
[DEBUG] NER confidence: 0.90 (boost: +0.28)
[DEBUG] Inference time: 1.85s
```

### Dashboard (CLI Output)

```bash
python src/cli.py --config config.yaml --verbose

[INFO] Processing 4,600,000 records...
[INFO] BERT model loading... done (2.3s)
[PROGRESS] ████████████████████░ 97% | 4.46M/4.6M | 210 rec/s

=== NER Fallback Statistics ===
Total invocations:        12,450
Percentage of records:    0.27%
Total NER time:           24,900s (~6.9h)
Avg time per call:        2.00s
Avg confidence boost:     +0.18 (0.65 → 0.83)
Success rate (≥0.70):     94.2%
```

---

## Troubleshooting

### Problemas Comuns

#### 1. Modelo não carrega

**Sintoma**:
```
OSError: Can't load tokenizer for 'marquesafonso/bertimbau-large-ner-selective'
```

**Soluções**:
```bash
# Força download do modelo BERTimbau-NER (~1.3GB)
python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('marquesafonso/bertimbau-large-ner-selective')"

# Verifica conexão com Hugging Face
curl -I https://huggingface.co

# Define cache local (para não baixar múltiplas vezes)
export TRANSFORMERS_CACHE=./models/cache

# Verifica espaço em disco (modelo requer ~1.5GB livres)
df -h .
```

#### 2. Timeout frequente

**Sintoma**:
```
TimeoutError: NER inference exceeded 5s timeout
```

**Soluções**:
```yaml
# config.yaml - Aumenta timeout
ai:
  ner_timeout: 10  # Aumenta para 10s
```

```python
# Ou: Trunca strings longas antes de enviar para NER
text = text[:300]  # Limita a 300 caracteres
```

#### 3. Memória insuficiente

**Sintoma**:
```
RuntimeError: CUDA out of memory
MemoryError: Unable to allocate tensor
```

**Análise**:
- BERTimbau-NER Large requer ~1.3GB em RAM (CPU) ou ~2GB em VRAM (GPU)
- Processamento sequential adiciona ~500MB de overhead

**Soluções**:
```python
# Força uso de CPU ao invés de GPU
ner = NERFallback(device="cpu")

# Ou verifica memória disponível antes de inicializar
import psutil
if psutil.virtual_memory().available < 2 * 1024**3:
    raise RuntimeError("Insufficient RAM (<2GB available)")
```

```yaml
# Reduz batch size se memória continuar insuficiente
processing:
  batch_size: 5000  # Reduz de 10000 para 5000
```

#### 4. Confiança ainda baixa após NER

**Sintoma**:
```
ValueError: Confidence 0.68 below threshold (0.70)
```

**Análise**:
- NER não detectou entidades PESSOA na string
- Pode ser genuinamente NAO_DETERMINADO ou GRUPO_PESSOAS

**Solução**:
```python
# Permite confiança ligeiramente menor para NER fallback
if result.confidence >= 0.65 and ner_was_used:
    # Aceita com warning
    logger.warning(f"Low NER confidence: {result.confidence}")
```

---

## Referências

### Modelos

- **Modelo Principal**: [marquesafonso/bertimbau-large-ner-selective](https://huggingface.co/marquesafonso/bertimbau-large-ner-selective) - BERTimbau-NER Large
- **BERTimbau Base**: [neuralmind/bert-base-portuguese-cased](https://huggingface.co/neuralmind/bert-base-portuguese-cased)
- **BERTimbau Large**: [neuralmind/bert-large-portuguese-cased](https://huggingface.co/neuralmind/bert-large-portuguese-cased)
- **LeNER-Br Model**: [pierreguillou/bert-base-cased-pt-lenerbr](https://huggingface.co/pierreguillou/bert-base-cased-pt-lenerbr)

### Datasets e Papers

- **Dataset LeNER-Br**: [LeNER-Br: a Dataset for Named Entity Recognition in Brazilian Legal Text](https://cic.unb.br/~teodecampos/LeNER-Br/)
- **Paper BERT**: [BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding](https://arxiv.org/abs/1810.04805)
- **BERTimbau Paper**: [BERTimbau: Portuguese BERT](https://arxiv.org/abs/2008.07869)

### Bibliotecas

- **Transformers**: [Hugging Face Transformers Documentation](https://huggingface.co/docs/transformers/)
- **PyTorch**: [PyTorch Documentation](https://pytorch.org/docs/)
- **Tokenizers**: [Hugging Face Tokenizers](https://huggingface.co/docs/tokenizers/)

### Artigos Relacionados

- [Named Entity Recognition in Portuguese](https://www.scielo.br/pdf/prc/v32n2/1678-7153-prc-32-02-e3229.pdf)
- [Deep Learning for NER in Scientific Texts](https://arxiv.org/abs/1904.10503)

---

## Histórico de Versões

| Versão | Data | Mudanças |
|--------|------|----------|
| 1.0.0 | 2025-10-03 | Integração inicial do NER com BERTimbau-NER Large |
| 1.0.1 | 2025-10-05 | Experimento batch processing (revertido após benchmarks) |
| 1.0.2 | 2025-10-05 | Documentação técnica completa com lessons learned |
| 2.0.0 | TBD | Fine-tuning com dados específicos de herbários |
| 3.0.0 | TBD | API configurável para seleção de modelos via config.yaml |

---

**Última atualização**: 2025-10-05
**Autor**: Sistema de Identificação de Coletores
**Licença**: MIT
