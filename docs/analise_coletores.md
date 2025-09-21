# Documentação: analise_coletores.py

## Descrição
O script `analise_coletores.py` realiza uma análise exploratória dos dados de coletores presentes na base de dados MongoDB. Esta análise é fundamental para entender os padrões, formatos e problemas nos dados antes de executar o processo de canonicalização.

## Funcionalidades Principais

### 1. Amostragem Estratificada por Kingdom
- **Plantae**: 3.000.000 registros aleatórios
- **Animalia**: 3.000.000 registros aleatórios
- **Total**: 6.000.000 registros para análise

### 2. Análise de Padrões de Nomes
- **Atomização**: Separação de múltiplos coletores em uma string
- **Formatos**: Identificação de padrões como:
  - `nome_simples`: "Silva"
  - `inicial_sobrenome`: "J. Silva"
  - `multiplas_palavras`: "João da Silva"
  - `maiusculo`: "SILVA"
  - `sobrenome_virgula_inicial`: "Silva, J."

### 3. Sistema de Classificação de Entidades
Classifica registros em quatro categorias principais com índice de confiança:

#### 👤 Pessoa (pessoa)
- Nome próprio de uma única pessoa
- Ex: "Silva, J.C.", "Maria Santos", "A. Costa", "G.A. Damasceno-Junior"
- Confiança baseada na presença de padrões de nomes individuais

#### 👥 Conjunto de Pessoas (conjunto_pessoas)
- Múltiplos nomes próprios para atomização
- Ex: "Silva, J.; Santos, M.; et al.", "Gonçalves, J.M.; A.O.Moraes"
- Contém nomes próprios separados por `;`, `&`, ou `et al.`

#### 🎯 Grupo de Pessoas (grupo_pessoas)
- Denominações genéricas SEM nomes próprios
- Ex: "Pesquisas da Biodiversidade", "Alunos da disciplina", "Equipe de pesquisa"
- Coletores não identificados ou anônimos

#### 🏢 Empresa/Instituição (empresa_instituicao)
- Acrônimos e códigos institucionais
- Ex: "EMBRAPA", "USP", "RB", "INPA", "Universidade Federal"
- Universidades, museus, herbários
- Empresas e órgãos governamentais

#### 📊 Índice de Confiança
- **Score 0.0-1.0**: Confiança na classificação
- **>0.9**: Alta confiança (acrônimos, palavras-chave específicas)
- **0.7-0.9**: Confiança moderada (padrões reconhecidos)
- **<0.7**: Baixa confiança (requer revisão manual)

### 4. Análise de Separadores
Detecta padrões utilizados para separar múltiplos coletores:
- `, + maiúscula`: "Silva, J. & Santos, M."
- `;`: "Silva; Santos"
- `&` ou `e`: "Silva & Santos"
- `et al.`: "Silva et al."
- `and`: "Silva and Santos"

### 5. Análise de Caracteres Especiais
Identifica caracteres não-padrão que podem indicar problemas de encoding ou formatação.

## Estrutura de Dados Analisados

### Entrada
- **Fonte**: Coleção `ocorrencias` no MongoDB
- **Campo**: `recordedBy`
- **Filtros**:
  - `kingdom`: "Plantae" ou "Animalia"
  - `recordedBy`: não vazio/nulo

### Saída
O script gera dois arquivos:

#### 1. Relatório Texto (`reports/analise_exploratoria_YYYYMMDD_HHMMSS.txt`)
```
================================================================================
RELATÓRIO DE ANÁLISE EXPLORATÓRIA - COLETORES
================================================================================
Data/Hora: 2025-09-20 05:48:44

ESTATÍSTICAS GERAIS
----------------------------------------
Total de registros analisados: 6,000,000
Registros válidos: 6,000,000
Registros vazios: 0
Total de nomes atomizados: 15,086,220
Taxa de atomização: 2.51 nomes/registro
Grupos/Projetos identificados: 1,250

DISTRIBUIÇÃO POR TIPO DE ENTIDADE
----------------------------------------
pessoa: 145,230 (72.6%)
conjunto_pessoas: 35,120 (17.6%)
grupo_pessoas: 15,340 (7.7%)
empresa_instituicao: 4,310 (2.2%)

DISTRIBUIÇÃO POR TAMANHO
----------------------------------------
curto (11-30): 115,660 (57.8%)
muito_curto (<=10): 44,446 (22.2%)
medio (31-60): 31,012 (15.5%)
...

EXEMPLOS DE GRUPOS/PROJETOS IDENTIFICADOS
----------------------------------------
  - Pesquisas da Biodiversidade
  - Alunos da disciplina de botânica
  - Equipe do Laboratório de Sistemática
  ...
```

#### 2. Dados JSON (`reports/dados_analise_YYYYMMDD_HHMMSS.json`)
Contém todas as estatísticas em formato estruturado para análises posteriores.

## Algoritmos Utilizados

### AtomizadorNomes
Utiliza padrões regex para separar múltiplos coletores:
```python
SEPARATOR_PATTERNS = [
    r'\s*[&e]\s+',           # & ou e
    r'\s*and\s+',            # and
    r'\s*;\s*',              # ;
    r'\s*,\s*(?=[A-Z])',     # , seguido de letra maiúscula
    r'\s*et\s+al\.?\s*',     # et al.
    r'\s*e\s+col\.?\s*',     # e col.
    ...
]
```

### Sistema de Classificação Inteligente
Utiliza algoritmo híbrido com múltiplos padrões e cálculo de confiança:

#### Detecção de Empresas/Instituições
```python
def _calculate_institution_confidence(text):
    confidence = 0.0

    # Acrônimos em maiúsculas (95% confiança)
    if re.match(r'^[A-Z]{2,8}$', text):
        confidence = 0.95

    # Códigos de herbário (95% confiança)
    if re.match(r'^[A-Z]{1,4}$', text) and len(text) <= 4:
        confidence = 0.95

    # Palavras-chave institucionais
    keywords = {
        'universidade': 0.90, 'instituto': 0.85,
        'embrapa': 0.95, 'ibama': 0.95
    }

    return confidence
```

#### Detecção de Conjunto de Pessoas
```python
def _calculate_conjunto_pessoas_confidence(text):
    confidence = 0.0

    # Múltiplos nomes separados por ; (80% confiança)
    if ';' in text:
        confidence = max(confidence, 0.8)

    # Padrão "et al." indica múltiplas pessoas (90% confiança)
    if re.search(r'et\s+al\.?|et\s+alli', text, re.IGNORECASE):
        confidence = max(confidence, 0.9)

    # Múltiplos padrões de nomes de pessoas
    matches = len(re.findall(r'[A-Z][a-z]+,\s*[A-Z]\.', text))
    if matches > 1:
        confidence = max(confidence, 0.85)

    return confidence
```

#### Detecção de Grupos Genéricos
```python
def _calculate_group_confidence(text):
    # Se contém nomes próprios, NÃO é grupo genérico
    if self._contains_proper_names(text):
        return 0.0

    # Palavras-chave de grupos genéricos
    keywords = {
        'equipe': 0.85, 'projeto': 0.75,
        'alunos': 0.90, 'pesquisa': 0.70
    }

    # Expressões específicas (alta confiança)
    if 'pesquisas da biodiversidade' in text.lower():
        confidence = 0.95

    return confidence
```

### Categorização de Formatos
- **nome_simples**: Nomes de uma palavra
- **maiusculo**: Nomes em caixa alta
- **inicial_sobrenome**: Formato "I. Sobrenome"
- **multiplas_palavras**: Nomes compostos
- **sobrenome_virgula_inicial**: Formato "Sobrenome, I."

## Configuração

### Parâmetros Principais
```python
# config/mongodb_config.py
ALGORITHM_CONFIG = {
    'sample_size': 3000000,  # Por kingdom
    ...
}

# Padrões de grupos de pessoas
GROUP_PATTERNS = [
    r'.*[Pp]esquisas?\s+(da\s+)?[Bb]iodiversidade.*',
    r'.*[Aa]lunos?\s+(da\s+)?[Dd]isciplina.*',
    r'.*[Ee]quipe.*',
    r'.*[Gg]rupo.*',
    ...
]

# Padrões de empresas/instituições
INSTITUTION_PATTERNS = [
    r'^[A-Z]{2,8}$',  # Acrônimos
    r'^[A-Z]{1,4}$',  # Códigos de herbário
    r'.*[Ii]nstituto.*',
    r'.*[Uu]niversidade.*',
    r'.*[Ee]mbrapa.*',
    r'.*[Ii]bama.*',
    ...
]
```

## Execução

### Pré-requisitos
- Conexão com MongoDB configurada
- Coleção `ocorrencias` com dados de `recordedBy` e `kingdom`
- Diretórios `logs/` e `reports/` criados

### Comando
```bash
cd src/
python analise_coletores.py
```

### Logs
- **Arquivo**: `../logs/analise_exploratoria.log`
- **Console**: Progresso em tempo real

## Métricas de Performance

### Tempo de Execução
- **6.000.000 registros**: ~60-90 minutos
- **Performance**: ~1.000-1.500 registros/segundo
- **Memória**: ~500MB RAM

### Dependências
- `pymongo`: Conexão MongoDB
- `pandas`: Manipulação de dados
- `collections.Counter`: Contadores eficientes
- `regex`: Padrões avançados

## Casos de Uso

### 1. Análise Inicial
Antes de executar a canonicalização, execute este script para:
- Entender a distribuição de formatos
- Identificar separadores comuns
- Detectar problemas de encoding
- Estimar tempo de processamento

### 2. Validação de Padrões
Após modificar padrões de separação ou detecção de grupos:
- Verificar se novos padrões são detectados
- Validar exemplos identificados
- Ajustar configurações

### 3. Análise Comparativa
Executar periodicamente para:
- Monitorar mudanças nos dados
- Comparar diferentes bases
- Avaliar melhorias no algoritmo

## Troubleshooting

### Problemas Comuns

1. **Erro de Conexão MongoDB**
   ```
   ServerSelectionTimeoutError
   ```
   - Verificar string de conexão
   - Confirmar acesso à rede
   - Validar credenciais

2. **Memória Insuficiente**
   - Reduzir tamanho da amostra
   - Processar por partes
   - Aumentar RAM disponível

3. **Encoding de Caracteres**
   - Verificar configuração UTF-8
   - Validar dados de origem
   - Ajustar padrões regex

### Logs de Debug
Para análise detalhada:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Exemplo de Uso
```python
from analise_coletores import AnalisadorColetores

# Inicializar analisador
analisador = AnalisadorColetores()

# Processar amostra
resultados = analisador.analisar_amostra(amostra_dados)

# Gerar relatório
relatorio = analisador.gerar_relatorio("meu_relatorio.txt")
```