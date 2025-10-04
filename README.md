# Sistema de Identificação e Canonicalização de Coletores de Plantas

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)
[![AI Powered](https://img.shields.io/badge/AI-BERT%20NER-orange.svg)](docs/NER_Implementation.md)

Sistema de processamento de linguagem natural (NLP) com **inteligência artificial** para identificar, classificar e canonicalizar nomes de coletores de plantas em registros de herbários digitais.

---

## 🤖 Destaques de Inteligência Artificial

Este sistema utiliza **modelos de IA de última geração** para processar nomes complexos de coletores:

- **BERT NER (Named Entity Recognition)**: Modelo `pierreguillou/bert-base-cased-pt-lenerbr` treinado em português brasileiro
- **Fallback Inteligente**: Ativado automaticamente para casos de baixa confiança (<70%)
- **Aceleração por GPU**: 66x mais rápido com CUDA (0.03s vs 2s por texto)
- **Processamento Híbrido**: Combina regras linguísticas + aprendizado profundo para máxima precisão

→ **[📖 Documentação Técnica Completa de IA](docs/NER_Implementation.md)**

---

## 📋 Sumário

- [Sobre o Projeto](#-sobre-o-projeto)
- [O Problema](#-o-problema)
- [A Solução](#-a-solução)
- [Arquitetura Técnica](#-arquitetura-técnica)
- [Instalação](#-instalação)
- [Uso](#-uso)
- [Estrutura do Projeto](#-estrutura-do-projeto)
- [Desenvolvimento](#-desenvolvimento)
- [Roadmap](#-roadmap)
- [Licença](#-licença)

---

## 🌿 Sobre o Projeto

Este projeto foi desenvolvido para resolver um problema crítico na curadoria de coleções botânicas digitais: a inconsistência na representação de nomes de coletores de plantas.

Em bancos de dados de herbários, o mesmo coletor pode aparecer de diversas formas:
- "Forzza, R.C."
- "Forzza, R."
- "R.C. Forzza"
- "Rafaela C. Forzza"

Essas variações dificultam análises quantitativas, estudos de redes de colaboração e a identificação correta de contribuições científicas individuais.

### Contexto

Com aproximadamente **4.6 milhões de registros** de plantas (kingdom = "Plantae") em bases de dados MongoDB de herbários brasileiros, a padronização manual é inviável. Este sistema automatiza o processo através de um pipeline de NLP robusto, eficiente e **potencializado por IA**.

---

## 🎯 O Problema

### Desafios Identificados

1. **Múltiplas representações do mesmo coletor**
   - Variações de formatação: "Silva, J." vs "J. Silva"
   - Diferentes níveis de detalhe: "Santos, M." vs "Maria Santos"
   - Erros de digitação e inconsistências

2. **Classificação ambígua**
   - Nomes próprios individuais vs. grupos de pessoas
   - Instituições vs. equipes de pesquisa
   - Registros sem identificação ("?", "sem coletor")

3. **Volume e Performance**
   - Processar 4.6 milhões de registros
   - Tempo limitado: máximo 6 horas de processamento
   - Requisito: ≥213 registros/segundo

4. **Dados não estruturados**
   - Strings livres com múltiplos formatos
   - Separadores variados (";", "&", "et al.")
   - Mistura de idiomas e caracteres especiais

---

## 💡 A Solução

### Pipeline de Processamento em 4 Etapas com IA

O sistema implementa um pipeline sequencial de transformação de dados potencializado por **aprendizado profundo**:

```
┌─────────────────────────────────────────────────────────────┐
│ ENTRADA: "Silva, J. & R.C. Forzza; Santos, M. et al."      │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ [1] CLASSIFICAÇÃO (com IA)                                  │
│     • Análise por regras linguísticas                       │
│     • Confiança inicial: 0.95 → "conjunto_pessoas"          │
│     ┌─────────────────────────────────────┐                 │
│     │ 🤖 AI FALLBACK (se confiança < 0.70)│                 │
│     │ • BERT NER analisa entidades        │                 │
│     │ • Boost de confiança: 0.65 → 0.82+  │                 │
│     │ • GPU: 0.03s por inferência         │                 │
│     │ • CPU: 2s por inferência            │                 │
│     └─────────────────────────────────────┘                 │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ [2] ATOMIZAÇÃO                                               │
│     Saída: ["Silva, J.", "R.C. Forzza", "Santos, M."]      │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ [3] NORMALIZAÇÃO                                             │
│     • Remove acentos, converte uppercase                    │
│     • Padroniza formato: "FORZZA, R.C."                     │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ [4] CANONICALIZAÇÃO                                          │
│     • Similaridade: Levenshtein + Jaro-Winkler + Fonética  │
│     • Agrupamento: "Forzza, R.C." ← variações similares     │
│     • Armazena em DuckDB com confiança                      │
└───────────────────────┬─────────────────────────────────────┘
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ SAÍDA: Entidades canônicas + variações + CSV                │
└─────────────────────────────────────────────────────────────┘
```

### 1. Classificação com IA

Categoriza cada string em **5 tipos** usando reconhecimento de padrões **híbrido** (regras + IA):

| Categoria | Descrição | Exemplo |
|-----------|-----------|---------|
| **Pessoa** | Nome próprio individual | "Silva, J.C.", "Maria Santos" |
| **Conjunto de Pessoas** | Múltiplos nomes para atomização | "Silva, J.; Santos, M." |
| **Grupo de Pessoas** | Denominação genérica sem nomes | "Equipe de pesquisa" |
| **Empresa/Instituição** | Acrônimos e códigos | "EMBRAPA", "USP", "INPA" |
| **Não Determinado** | Sem identificação | "?", "sem coletor" |

**Confiança mínima**: 0.70

#### 🤖 Fallback de IA (IMPLEMENTADO)

Para strings complexas ou com confiança < 0.70:
- **Modelo**: `pierreguillou/bert-base-cased-pt-lenerbr` (Portuguese BERT)
- **Ativação**: Automática quando confiança < 0.70
- **Boost de Confiança**:
  - Pessoa detectada (score > 0.85): +0.15
  - Pessoa detectada (score > 0.70): +0.10
  - Pessoa detectada (score < 0.70): +0.05
  - Organização detectada: +0.05
- **Performance GPU** (NVIDIA GTX 1060): 0.03s por texto
- **Performance CPU**: 2s por texto
- **Uso de Memória GPU**: 414 MB
- **Lazy Loading**: Modelo carrega apenas quando necessário

→ **[Detalhes técnicos do BERT NER](docs/NER_Implementation.md)**

### 2. Atomização

Separa conjuntos de pessoas em nomes individuais:

- **Separadores reconhecidos**: `;` (ponto-e-vírgula), `&` (e comercial), `et al.`
- **Preserva formatação original** para rastreabilidade
- **Registra ordem** dos nomes na string original

**Exemplo**:
```python
Input:  "Silva, J. & R.C. Forzza; Santos, M. et al."
Output: [
    {"text": "Silva, J.", "position": 0, "separator": "&"},
    {"text": "R.C. Forzza", "position": 1, "separator": ";"},
    {"text": "Santos, M.", "position": 2, "separator": "et al."}
]
```

### 3. Normalização

Padroniza nomes para comparação, aplicando **3 regras**:

1. **Remove espaços extras**: `"  Silva,J.C. "` → `"Silva,J.C."`
2. **Padroniza pontuação**: `"Silva,J"` → `"Silva, J"`
3. **Converte para maiúsculas**: `"Silva, j.c."` → `"SILVA, J.C."`

**Importante**: A formatação original é **preservada** para exibição, enquanto a versão normalizada é usada apenas para matching.

### 4. Canonicalização

Agrupa variações similares sob um **nome canônico** usando algoritmos de similaridade combinados:

#### Algoritmos de Similaridade

| Algoritmo | Peso | Propósito |
|-----------|------|-----------|
| **Levenshtein** | 40% | Detecta erros de digitação e transposições |
| **Jaro-Winkler** | 40% | Otimizado para strings curtas (sobrenomes) |
| **Phonético (Metaphone)** | 20% | Captura variações fonéticas |

**Score final**: Média ponderada ≥ 0.70 para agrupamento

**Exemplo de agrupamento**:
```
Variações detectadas:
- "Forzza, R.C." (1523 ocorrências)
- "Forzza, R." (847 ocorrências)
- "R.C. Forzza" (234 ocorrências)
- "Rafaela C. Forzza" (89 ocorrências)

Nome canônico: "Forzza, R.C."
Total de ocorrências: 2693
```

### Formato Canônico

Para entidades do tipo **Pessoa**, o sistema aplica o formato padrão:

**"Sobrenome, Iniciais"**

Exemplos:
- Todas as variações de "Forzza" → `"Forzza, R.C."`
- Todas as variações de "Silva" → `"Silva, J."`

---

## 🏗️ Arquitetura Técnica

### Stack Tecnológico

- **Linguagem**: Python 3.11+
- **Inteligência Artificial**:
  - **`transformers`** - Hugging Face BERT models
  - **`torch`** - PyTorch para inferência de deep learning (suporta CUDA 12.4+)
  - Modelo: `pierreguillou/bert-base-cased-pt-lenerbr` (414MB na GPU)
- **Processamento NLP**:
  - `python-Levenshtein` - Cálculo de distância de edição
  - `jellyfish` - Jaro-Winkler e algoritmos fonéticos (Metaphone, Soundex)
- **Banco de Dados**:
  - **MongoDB** - Fonte de dados (4.6M registros)
  - **DuckDB** - Armazenamento local otimizado para análises
- **Manipulação de Dados**:
  - `pymongo` - Cliente MongoDB
  - `pandas` - Exportação CSV e processamento tabular
  - `pydantic` - Validação de schemas e type safety
- **Interface**:
  - `click` - CLI intuitivo
  - `tqdm` - Barras de progresso

### Modelo de Dados

```sql
-- Tabela única desnormalizada (DuckDB)
CREATE TABLE canonical_entities (
  id INTEGER PRIMARY KEY,
  canonicalName TEXT NOT NULL,
  entityType TEXT CHECK(entityType IN
    ('Pessoa', 'GrupoPessoas', 'Empresa', 'NaoDeterminado')),
  classification_confidence REAL CHECK(0.70 <= value <= 1.0),
  grouping_confidence REAL CHECK(0.70 <= value <= 1.0),
  variations JSON NOT NULL, -- Array de variações
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

**Variações em JSON**:
```json
[
  {
    "variation_text": "Forzza, R.C.",
    "occurrence_count": 1523,
    "association_confidence": 0.95,
    "first_seen": "2025-10-03T10:15:00Z",
    "last_seen": "2025-10-03T14:30:00Z"
  }
]
```

### Performance

#### Requisitos

- **Throughput**: ≥213 registros/segundo
- **Tempo total**: ≤6 horas para 4.6M registros
- **Overhead de IA**: ~0.03s por caso com GPU (66x mais rápido que CPU)
- **Memória**: Streaming eficiente (sem carregar todos os registros em RAM)

#### Estratégia de Paralelização

```
MongoDB (4.6M registros)
    ↓
Batch Reader (chunks de 10K)
    ↓
Worker Pool (processamento sequencial - DuckDB não suporta paralelo)
    ↓ [Pipeline completo por batch]
    ↓
Results Aggregator (DuckDB com WAL)
    ↓
Banco de Dados Local
```

- **Processamento Sequencial**: DuckDB não suporta escritas paralelas
- **Batch processing**: Chunks de 10.000 registros
- **Cursor streaming**: MongoDB batch_size=1000 (eficiência de memória)
- **Modelo BERT**: Carregado uma vez em memória e cacheado (GPU se disponível)

### Garantias de Qualidade

#### Limiar de Confiança

Todas as operações respeitam **confiança mínima de 0.70**:

- ✅ Confiança ≥ 0.70: Aceita automaticamente
- 🤖 Confiança < 0.70: Tenta fallback de IA BERT
- ⚠️ Ainda < 0.70 após IA: Sinaliza para revisão manual

#### Type Safety

- **Pydantic models**: Validação em runtime
- **mypy strict mode**: Verificação estática de tipos
- **100% type hints**: Todo código público tipado

#### Testes

- **Cobertura mínima**: 80% (100% em lógica de negócio)
- **Contract tests**: Schemas de entrada/saída (incluindo NER)
- **Integration tests**: 7 cenários de aceitação
- **Performance tests**: Benchmarks com pytest-benchmark

---

## 🚀 Instalação

### Pré-requisitos

- Python 3.11 ou superior (Python 3.13 testado e funcionando)
- MongoDB rodando (local ou remoto)
- 4GB RAM mínimo (8GB recomendado)
- **Opcional**: GPU NVIDIA com CUDA para aceleração de IA (66x mais rápido)

### Instalação Padrão (CPU)

1. **Clone o repositório**
```bash
git clone https://github.com/biopinda/coletores-BO.git
cd coletores-BO
```

2. **Crie um ambiente virtual**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **Instale as dependências**
```bash
pip install -r requirements-minimal.txt
```

### Instalação com GPU (Recomendado)

Para aproveitar aceleração por GPU (66x mais rápido no NER):

#### Windows (uma vez, requer privilégios de administrador):

```powershell
# Habilitar caminhos longos (resolve erro de path length do PyTorch)
Set-ItemProperty -Path 'HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem' -Name LongPathsEnabled -Value 1
```

#### Instalar PyTorch com CUDA:

```bash
# Python 3.13 (nightly build)
pip install --pre torch --index-url https://download.pytorch.org/whl/nightly/cu124

# Python 3.11-3.12 (stable)
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

#### Instalar demais dependências:

```bash
pip install -r requirements.txt
```

**Nota**: O primeiro uso fará download automático do modelo BERT (~420MB) do Hugging Face.

### Configuração

Edite `config.yaml`:
```yaml
mongodb:
  uri: "mongodb://localhost:27017"
  database: "dwc2json"
  collection: "ocorrencias"
  filter: { kingdom: "Plantae" }

local_db:
  type: "duckdb"
  path: "./data/canonical_entities.db"

processing:
  batch_size: 10000
  confidence_threshold: 0.70

output:
  csv_path: "./output/canonical_report.csv"
```

---

## 💻 Uso

### Processamento Básico

```bash
python src/cli.py --config config.yaml
```

### Opções Avançadas

```bash
# Processar apenas primeiros 1000 registros (teste)
python src/cli.py --config config.yaml --max-records 1000

# Especificar arquivo de saída CSV customizado
python src/cli.py --config config.yaml
```

### Métricas de IA

O sistema exibe automaticamente métricas de uso do NER fallback:

```
✅ Pipeline complete!
   Processed: 1000 records
   Time: 87.0s
   Rate: 11.5 rec/sec
   NER fallback used: 0 times
```

### Saídas Geradas

1. **Banco de dados local**: `./data/canonical_entities.db` (DuckDB)
   - Contém todas as entidades canônicas e variações
   - Persistente para análises futuras

2. **Relatório CSV**: `./output/canonical_report.csv`
   - 3 colunas: `canonicalName`, `variations`, `occurrenceCounts`
   - Variações separadas por `;`
   - Contagens alinhadas com variações

**Exemplo do CSV**:

```csv
canonicalName,variations,occurrenceCounts
"FORZZA, R.C.","FORZZA, R.C.;R.C. FORZZA;RAFAELA C. FORZZA","1523;847;234"
"SILVA, J.","SILVA, J.;J. SILVA","2891;1205"
```

3. **Documentação de regras**: `./docs/rules.md`
   - Regras editáveis do algoritmo
   - Permite refinamento iterativo

---

## 📂 Estrutura do Projeto

```
coletores-BO/
├─ src/                        # Código-fonte principal
│   ├─ pipeline/               # Estágios do pipeline
│   │   ├─ classifier.py       # Classificação (com IA)
│   │   ├─ ner_fallback.py     # 🤖 BERT NER fallback (NOVO)
│   │   ├─ atomizer.py         # Atomização
│   │   ├─ normalizer.py       # Normalização
│   │   └─ canonicalizer.py    # Canonicalização
│   ├─ algorithms/             # Algoritmos de similaridade
│   │   ├─ similarity.py       # Levenshtein, Jaro-Winkler
│   │   └─ phonetic.py         # Metaphone, Soundex
│   ├─ models/                 # Modelos de dados
│   │   ├─ entities.py         # Entidades Pydantic
│   │   └─ contracts.py        # Contratos de dados
│   ├─ storage/                # Adaptadores de armazenamento
│   │   ├─ mongodb_client.py   # Cliente MongoDB
│   │   └─ local_db.py         # Cliente DuckDB
│   ├─ cli.py                  # Interface CLI
│   └─ config.py               # Gerenciamento de configuração
│
├─ tests/                      # Testes automatizados
│   ├─ contract/               # Testes de contrato (inc. NER)
│   ├─ integration/            # Testes de integração
│   └─ unit/                   # Testes unitários
│
├─ docs/                       # Documentação
│   ├─ fix.md                  # Instruções de melhorias
│   └─ NER_Implementation.md   # 🤖 Documentação técnica de IA (NOVO)
│
├─ config.yaml                 # Configuração principal
├─ requirements.txt            # Dependências completas (com GPU)
├─ requirements-minimal.txt    # Dependências mínimas (CPU only)
└─ README.md                   # Este arquivo
```

---

## 🛠️ Desenvolvimento

### Executar Testes

```bash
# Todos os testes
pytest tests/

# Apenas testes de contrato
pytest tests/contract/

# Com cobertura
pytest --cov=src --cov-report=term-missing

# Testes específicos de IA
pytest tests/contract/test_ner_schema.py -v
```

### Verificação de Qualidade

```bash
# Type checking
mypy src/ --strict

# Linting
ruff check src/

# Formatação
black --check src/
```

### Adicionar Novos Padrões de Classificação

Edite `src/pipeline/classifier.py`:

```python
# Exemplo: adicionar novo padrão institucional
if re.match(r'^SEU_PADRAO$', text):
    return ClassificationOutput(
        original_text=text,
        category=ClassificationCategory.EMPRESA,
        confidence=0.95,
        patterns_matched=["seu_padrao"],
        should_atomize=False
    )
```

---

## 🗺️ Roadmap

### Fase 1: Implementação Core ✅

- [x] Estrutura do projeto
- [x] Especificações e planejamento
- [x] Contratos de interface
- [x] **Integração de IA (BERT NER com GPU)**
- [x] Implementação completa do pipeline
- [x] Testes automatizados (49/49 contract tests)
- [ ] Validação com 4.6M registros

### Fase 2: Refinamento (Futuro)

- [ ] Interface web para revisão manual de baixa confiança
- [ ] Dashboard de métricas e visualizações de IA
- [ ] API REST para integração com outros sistemas
- [ ] Fine-tuning do modelo BERT com dados específicos de herbários

### Fase 3: Escalabilidade (Futuro)

- [ ] Processamento distribuído (considerando limitação do DuckDB)
- [ ] Cache inteligente de similaridades
- [ ] Exportação para múltiplos formatos (JSON, Parquet)
- [ ] Versionamento de entidades canônicas

---

## 📊 Especificações Técnicas Detalhadas

Para informações técnicas completas, consulte:

- **🤖 Documentação de IA**: [`docs/NER_Implementation.md`](docs/NER_Implementation.md) ← **NOVO**
- **Instruções de Melhorias**: [`docs/fix.md`](docs/fix.md)

---

## 📄 Licença

Este projeto está licenciado sob a [Creative Commons Attribution 4.0 International License (CC BY 4.0)](https://creativecommons.org/licenses/by/4.0/).

Você é livre para:
- **Compartilhar** — copiar e redistribuir o material em qualquer meio ou formato
- **Adaptar** — remixar, transformar e construir sobre o material para qualquer propósito, mesmo comercialmente

Sob os seguintes termos:
- **Atribuição** — Você deve dar crédito apropriado, fornecer um link para a licença e indicar se mudanças foram feitas

Veja o arquivo [LICENSE](LICENSE) para detalhes completos.

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Por favor:

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

---

## 📧 Contato

**Projeto**: Sistema de Identificação e Canonicalização de Coletores de Plantas
**Repositório**: [https://github.com/biopinda/coletores-BO](https://github.com/biopinda/coletores-BO)
**Organização**: BioPinda

---

## 🙏 Agradecimentos

- Herbários brasileiros que disponibilizam dados abertos
- Comunidade científica de botânica sistemática
- Desenvolvedores das bibliotecas open-source utilizadas
- **Hugging Face** pela plataforma de modelos de IA
- **Pierre Guillou** pelo modelo BERT em português brasileiro

---

Desenvolvido com 🌿 e 🤖 para a ciência botânica brasileira
