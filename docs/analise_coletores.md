# Documentação: analise_coletores.py

## Descrição
O script `analise_coletores.py` realiza uma análise exploratória dos dados de coletores presentes na base de dados MongoDB. Esta análise é fundamental para entender os padrões, formatos e problemas nos dados antes de executar o processo de canonicalização.

## Funcionalidades Principais

### 1. Amostragem Estratificada por Kingdom
- **Plantae**: 100.000 registros aleatórios
- **Animalia**: 100.000 registros aleatórios
- **Total**: 200.000 registros para análise

### 2. Análise de Padrões de Nomes
- **Atomização**: Separação de múltiplos coletores em uma string
- **Formatos**: Identificação de padrões como:
  - `nome_simples`: "Silva"
  - `inicial_sobrenome`: "J. Silva"
  - `multiplas_palavras`: "João da Silva"
  - `maiusculo`: "SILVA"
  - `sobrenome_virgula_inicial`: "Silva, J."

### 3. Detecção de Grupos/Projetos
Identifica registros que representam grupos ou projetos ao invés de pessoas individuais:
- Pesquisas da Biodiversidade
- Alunos da disciplina de botânica
- Equipes, laboratórios, institutos
- Coletores não identificados

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
Total de registros analisados: 200,000
Registros válidos: 200,000
Registros vazios: 0
Total de nomes atomizados: 502,874
Taxa de atomização: 2.51 nomes/registro
Grupos/Projetos identificados: 1,250

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

### Detecção de Grupos
Utiliza padrões regex para identificar grupos/projetos:
```python
GROUP_PATTERNS = [
    r'.*[Pp]esquisas?\s+(da\s+)?[Bb]iodiversidade.*',
    r'.*[Aa]lunos?\s+(da\s+)?[Dd]isciplina.*',
    r'.*[Ee]quipe.*',
    r'.*[Gg]rupo.*',
    ...
]
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
    'sample_size': 100000,  # Por kingdom
    ...
}

# Padrões de grupos
GROUP_PATTERNS = [
    r'.*[Pp]esquisas?\s+(da\s+)?[Bb]iodiversidade.*',
    r'.*[Aa]lunos?\s+(da\s+)?[Dd]isciplina.*',
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
- **200.000 registros**: ~2-3 minutos
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