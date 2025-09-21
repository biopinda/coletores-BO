# Algoritmos de Canonicalização de Coletores

## Visão Geral

Este documento descreve as estratégias técnicas e algoritmos utilizados no sistema de canonicalização de nomes de coletores biológicos. O sistema implementa um pipeline de quatro etapas principais: **Classificação**, **Atomização**, **Normalização** e **Canonicalização**.

## Pipeline de Processamento

```
Entrada: "Silva, J. & R.C. Forzza; Santos, M. et al."
    ↓
[1] CLASSIFICAÇÃO → "conjunto_pessoas" (confiança: 0.95)
    ↓
[2] ATOMIZAÇÃO → ["Silva, J.", "R.C. Forzza", "Santos, M."]
    ↓
[3] NORMALIZAÇÃO → Para cada nome individual
    ↓
[4] CANONICALIZAÇÃO → Agrupamento por similaridade
    ↓
Saída: Coletores canônicos com variações agrupadas
```

---

## 1. Sistema de Classificação de Entidades

### 1.1 Estratégia Multi-Pattern

O classificador utiliza três conjuntos de padrões regex para identificar tipos de entidades:

- **`GROUP_PATTERNS`**: Detecta grupos/projetos/equipes
- **`INSTITUTION_PATTERNS`**: Identifica empresas/universidades/códigos
- **`SEPARATOR_PATTERNS`**: Reconhece múltiplos coletores

### 1.2 Algoritmo de Classificação

```python
def classify_entity_type(text: str) -> Dict[str, any]:
    # 1. Detecção de ausência
    if matches_absence_patterns(text):
        return {'tipo': 'ausencia_coletor', 'confianca': 1.0}

    # 2. Detecção de instituições (alta prioridade)
    inst_score = calculate_institution_score(text)
    if inst_score > 0.7:
        return {'tipo': 'empresa_instituicao', 'confianca': inst_score}

    # 3. Detecção de grupos
    group_score = calculate_group_score(text)
    if group_score > 0.6:
        return {'tipo': 'grupo_pessoas', 'confianca': group_score}

    # 4. Detecção de múltiplos coletores
    if has_separators(text):
        return {'tipo': 'conjunto_pessoas', 'confianca': 0.9}

    # 5. Default: pessoa individual
    return {'tipo': 'pessoa', 'confianca': 0.8}
```

### 1.3 Scoring de Confiança

- **Acrônimos universitários**: `0.95` (ex: "USP", "UFRJ")
- **Palavras institucionais**: `0.85` (ex: "Universidade", "Instituto")
- **Separadores múltiplos**: `0.90` (ex: "&", "et al.")
- **Padrões de grupo**: `0.75` (ex: "Equipe de pesquisa")

---

## 2. Atomização de Nomes Múltiplos

### 2.1 Padrões de Separação

O sistema reconhece 9 padrões principais de separação:

```regex
r'\s*[&e]\s+'           # & ou e
r'\s*and\s+'            # and
r'\s*;\s*'              # ;
r'\s*\|\s*'             # | (pipe)
r'\s*,\s*(?=[A-Z])'     # , seguido de maiúscula
r'\s*et\s+al\.?\s*'     # et al.
r'\s*e\s+col\.?\s*'     # e col.
r'\s*com\s+'            # com
r'\s*with\s+'           # with
```

### 2.2 Algoritmo de Atomização

```python
def atomizar(text: str) -> List[str]:
    # 1. Classificação prévia
    if not is_atomizable_type(text):
        return [text]  # Retorna como único item

    # 2. Aplicação sequencial de padrões
    segments = [text]
    for pattern in SEPARATOR_PATTERNS:
        new_segments = []
        for segment in segments:
            new_segments.extend(split_by_pattern(segment, pattern))
        segments = new_segments

    # 3. Limpeza e validação
    return [clean_name(seg) for seg in segments if is_valid_name(seg)]
```

### 2.3 Validação de Segmentos

Cada segmento atomizado passa por validação:
- **Tamanho mínimo**: 2 caracteres
- **Caracteres válidos**: Letras, espaços, pontos, vírgulas, hífens
- **Padrão de nome**: Deve conter pelo menos uma letra maiúscula

---

## 3. Normalização de Nomes Individuais

### 3.1 Extração de Componentes

```python
def normalizar(nome: str) -> Dict[str, any]:
    return {
        'nome_original': nome,
        'nome_limpo': clean_text(nome),
        'nome_normalizado': normalize_case(nome),
        'sobrenome': extract_surname(nome),
        'sobrenome_normalizado': normalize_surname(nome),
        'iniciais': extract_initials(nome),
        'tem_inicial': has_initials(nome),
        'chaves_busca': generate_phonetic_keys(nome)
    }
```

### 3.2 Estratégias de Extração

#### Sobrenome
1. **Formato "Sobrenome, I."**: Extrai texto antes da vírgula
2. **Formato "I. Sobrenome"**: Extrai última palavra
3. **Múltiplas palavras**: Usa heurísticas de capitalização

#### Iniciais
- Extrai letras maiúsculas seguidas de ponto
- Reconhece padrões como "J.C.", "R.", "A.B."
- Valida se são realmente iniciais (não acrônimos)

### 3.3 Normalização Textual

```python
def normalize_surname(surname: str) -> str:
    # 1. Remove acentos
    text = unidecode(surname)

    # 2. Converte para minúsculas
    text = text.lower()

    # 3. Remove caracteres especiais
    text = re.sub(r'[^a-z\s]', '', text)

    # 4. Remove espaços extras
    text = re.sub(r'\s+', '', text)

    return text
```

---

## 4. Algoritmos de Similaridade

### 4.1 Distância de Levenshtein

**Uso**: Medição de diferenças entre strings de caracteres.

```python
def similarity_score(name1: str, name2: str) -> float:
    distance = Levenshtein.distance(name1, name2)
    max_len = max(len(name1), len(name2))
    return 1.0 - (distance / max_len) if max_len > 0 else 0.0
```

**Aplicação**:
- Comparação de sobrenomes normalizados
- Tolerância a typos e variações menores
- Exemplo: "Silva" vs "Silv" → 0.8 de similaridade

### 4.2 Soundex

**Uso**: Codificação fonética para nomes similares foneticamente.

```python
import phonetics

def generate_soundex(text: str) -> str:
    try:
        return phonetics.soundex(text)
    except:
        return ''
```

**Características**:
- Código de 4 caracteres (1 letra + 3 dígitos)
- Agrupa nomes com som similar
- Exemplo: "Silva" → "S410", "Sylva" → "S410"

### 4.3 Metaphone

**Uso**: Algoritmo fonético mais preciso que Soundex.

```python
def generate_metaphone(text: str) -> str:
    try:
        return phonetics.metaphone(text)
    except:
        return ''
```

**Vantagens**:
- Melhor para nomes não-ingleses
- Mais sensível a variações fonéticas
- Exemplo: "Forzza" → "FRTS", "Forza" → "FRTS"

---

## 5. Estratégia de Canonicalização

### 5.1 Algoritmo de Scoring Composto

O sistema calcula similaridade usando pesos balanceados:

```python
def calculate_similarity(nome1: Dict, nome2: Dict) -> float:
    # Peso 50%: Similaridade do sobrenome
    surname_sim = levenshtein_similarity(
        nome1['sobrenome_normalizado'],
        nome2['sobrenome_normalizado']
    )

    # Peso 30%: Compatibilidade de iniciais
    initial_compat = calculate_initial_compatibility(
        nome1['iniciais'],
        nome2['iniciais']
    )

    # Peso 20%: Similaridade fonética
    phonetic_sim = calculate_phonetic_similarity(
        nome1['chaves_busca'],
        nome2['chaves_busca']
    )

    return (0.5 * surname_sim) + (0.3 * initial_compat) + (0.2 * phonetic_sim)
```

### 5.2 Compatibilidade de Iniciais

```python
def calculate_initial_compatibility(initials1: List[str], initials2: List[str]) -> float:
    if not initials1 or not initials2:
        return 0.5  # Neutro quando uma não tem iniciais

    # Verifica se são subconjuntos compatíveis
    set1, set2 = set(initials1), set(initials2)

    if set1.issubset(set2) or set2.issubset(set1):
        return 1.0  # Totalmente compatível

    # Calcula interseção
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))

    return intersection / union if union > 0 else 0.0
```

### 5.3 Similaridade Fonética

```python
def calculate_phonetic_similarity(keys1: Dict, keys2: Dict) -> float:
    soundex_match = 1.0 if keys1['soundex'] == keys2['soundex'] else 0.0
    metaphone_match = 1.0 if keys1['metaphone'] == keys2['metaphone'] else 0.0

    # Metaphone tem peso maior (mais preciso)
    return (0.4 * soundex_match) + (0.6 * metaphone_match)
```

---

## 6. Estratégias de Agrupamento

### 6.1 Busca de Candidatos

```python
def buscar_candidatos(nome_normalizado: Dict) -> List[Dict]:
    candidatos = []

    # 1. Busca exata por sobrenome normalizado
    candidatos.extend(
        buscar_por_sobrenome(nome_normalizado['sobrenome_normalizado'])
    )

    # 2. Busca fonética por Soundex
    candidatos.extend(
        buscar_por_soundex(nome_normalizado['chaves_busca']['soundex'])
    )

    # 3. Busca fonética por Metaphone
    candidatos.extend(
        buscar_por_metaphone(nome_normalizado['chaves_busca']['metaphone'])
    )

    return remove_duplicates(candidatos)
```

### 6.2 Decisão de Agrupamento

```python
def processar_nome(nome_normalizado: Dict) -> Dict:
    candidatos = buscar_candidatos(nome_normalizado)

    if not candidatos:
        return criar_novo_canonico(nome_normalizado)

    melhor_match = encontrar_melhor_match(nome_normalizado, candidatos)

    if melhor_match['score'] >= SIMILARITY_THRESHOLD:  # 0.85
        return agrupar_com_existente(nome_normalizado, melhor_match)
    else:
        return criar_novo_canonico(nome_normalizado)
```

### 6.3 Merge de Variações

```python
def merge_variacoes(existente: Dict, novo: Dict):
    # 1. Atualiza frequências
    for nova_variacao in novo['variacoes']:
        forma = nova_variacao['forma_original']

        if forma in variacoes_existentes:
            # Soma frequências
            existente_var['frequencia'] += nova_variacao['frequencia']
            existente_var['ultima_ocorrencia'] = max(timestamps)
        else:
            # Adiciona nova variação
            existente['variacoes'].append(nova_variacao)

    # 2. Escolhe nome canônico mais específico
    if nome_mais_especifico(novo['coletor_canonico'], existente['coletor_canonico']):
        existente['coletor_canonico'] = novo['coletor_canonico']
        existente['iniciais'] = novo['iniciais']

    # 3. Atualiza totais e metadados
    existente['total_registros'] = sum(v['frequencia'] for v in existente['variacoes'])
    existente['metadados']['ultima_atualizacao'] = datetime.now()
```

---

## 7. Otimizações de Performance

### 7.1 Cache em Memória

- **Coletores canônicos**: Cache dos coletores mais acessados
- **Chaves fonéticas**: Cache de cálculos Soundex/Metaphone
- **Resultados de busca**: Cache de candidatos por sobrenome

### 7.2 Índices MongoDB

```javascript
// Índices criados automaticamente
db.coletores.createIndex({"sobrenome_normalizado": 1})
db.coletores.createIndex({"variacoes.forma_original": 1})
db.coletores.createIndex({"indices_busca.soundex": 1})
db.coletores.createIndex({"indices_busca.metaphone": 1})
db.coletores.createIndex([
    {"sobrenome_normalizado": 1},
    {"indices_busca.soundex": 1}
])
```

### 7.3 Processamento em Lotes

- **Tamanho do lote**: 10.000 registros
- **Checkpoints**: A cada 50.000 registros processados
- **Retry logic**: 3 tentativas com backoff exponencial

---

## 8. Configurações e Thresholds

### 8.1 Parâmetros Principais

```python
ALGORITHM_CONFIG = {
    'similarity_threshold': 0.85,      # Limiar para agrupamento
    'confidence_threshold': 0.7,       # Limiar para revisão automática
    'levenshtein_max_distance': 3,     # Distância máxima permitida
    'batch_size': 10000,               # Registros por lote
    'sample_size': 3000000,            # Amostra para análise
}
```

### 8.2 Impacto dos Thresholds

- **`similarity_threshold` baixo** (0.75): Mais agrupamento, possível over-merging
- **`similarity_threshold` alto** (0.95): Menos agrupamento, mais coletores únicos
- **`confidence_threshold` baixo** (0.5): Menos casos para revisão manual
- **`confidence_threshold` alto** (0.9): Mais casos marcados para revisão

---

## 9. Validação e Qualidade

### 9.1 Métricas de Qualidade

```python
def calcular_metricas_qualidade(coletor: Dict) -> Dict:
    return {
        'taxa_canonicalizacao': len(variacoes) / 1,
        'consistencia_iniciais': validate_initial_consistency(coletor),
        'coerencia_sobrenome': validate_surname_coherence(coletor),
        'distribuicao_frequencias': analyze_frequency_distribution(coletor)
    }
```

### 9.2 Detecção de Problemas

- **Sobrenomes inconsistentes**: Distância Levenshtein > 2 entre variações
- **Iniciais conflitantes**: Iniciais incompatíveis entre variações
- **Frequências anômalas**: Distribuições muito desbalanceadas
- **Grupos heterogêneos**: Mistura de pessoas/instituições

---

## 10. Casos de Uso e Exemplos

### 10.1 Agrupamento Bem-Sucedido

```
Entrada: ["FORZZA", "Forzza, R.", "R.C. Forzza", "Rafael C. Forzza"]

Processo:
1. Normalização: sobrenome_normalizado = "forzza"
2. Chaves fonéticas: soundex="F620", metaphone="FRTS"
3. Cálculo similaridade: 0.95 (acima do threshold)
4. Agrupamento: 4 variações → 1 coletor canônico

Resultado:
{
  "coletor_canonico": "Forzza, R.C.",
  "sobrenome_normalizado": "forzza",
  "iniciais": ["R", "C"],
  "variacoes": [
    {"forma_original": "FORZZA", "frequencia": 1250},
    {"forma_original": "Forzza, R.", "frequencia": 800},
    {"forma_original": "R.C. Forzza", "frequencia": 950},
    {"forma_original": "Rafael C. Forzza", "frequencia": 45}
  ],
  "confianca_canonicalizacao": 0.95
}
```

### 10.2 Separação Correta

```
Entrada: ["Silva, J.", "Silveira, J."]

Processo:
1. Sobrenomes: "silva" vs "silveira"
2. Distância Levenshtein: 0.75 (abaixo do threshold 0.85)
3. Chaves fonéticas: diferentes
4. Decisão: Manter separados

Resultado: 2 coletores canônicos distintos
```

---

## 11. Limitações e Casos Especiais

### 11.1 Limitações Conhecidas

- **Nomes muito curtos**: Difficuldade com iniciais únicas (ex: "A", "B")
- **Nomes compostos complexos**: "Silva-Santos" vs "Silva Santos"
- **Transliterações**: Variações de idiomas diferentes
- **Homônimos**: Pessoas diferentes com nomes idênticos

### 11.2 Estratégias de Mitigação

- **Análise contextual**: Uso de kingdoms para desambiguação
- **Revisão manual**: Casos de baixa confiança marcados para validação
- **Validação cruzada**: Verificação de consistência temporal e geográfica
- **Feedback iterativo**: Ajuste de parâmetros baseado em resultados

---

## Referências Técnicas

- **Levenshtein Distance**: [Edit Distance Algorithm](https://en.wikipedia.org/wiki/Levenshtein_distance)
- **Soundex**: [Phonetic Algorithm for Names](https://en.wikipedia.org/wiki/Soundex)
- **Metaphone**: [Improved Phonetic Algorithm](https://en.wikipedia.org/wiki/Metaphone)
- **MongoDB Text Indexing**: [MongoDB Documentation](https://docs.mongodb.com/manual/text-indexes/)
- **Python phonetics library**: [GitHub Repository](https://github.com/Lilykos/phonetics)