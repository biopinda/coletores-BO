# Harmonização do nome de coletores de amostras de herbário e coleções biológicas no Brasil

> **Nota**: Este repositório foi migrado para https://github.com/biopinda/coletoresDWC2JSON

Este projeto implementa um algoritmo para canonicalização de nomes de coletores de amostras biológicas botânicas e zoológicas, processando dados armazenados em MongoDB.

## Projeto Relacionado

Este projeto está associado ao [DarwinCoreJSON](https://github.com/biopinda/DarwinCoreJSON), um sistema para conversão de dados de biodiversidade para o padrão Darwin Core em formato JSON. O **coletoresDWC2JSON** atua como um componente de melhoria da qualidade dos dados, especificamente focado na normalização e canonicalização dos nomes de coletores no banco de dados gerado pelo DarwinCoreJSON, aumentando a consistência e facilitando análises posteriores.

## Principais Funcionalidades

### 🔬 Análise por Kingdom
- **Amostragem estratificada**: 100.000 registros de Plantae + 100.000 de Animalia
- **Especialização detectada**: Identifica coletores especializados em botânica ou zoologia
- **Análise comparativa**: Estatísticas específicas por reino biológico

### 🏛️ Sistema de Classificação de Entidades
- **Três categorias**: Pessoa, Grupo de Pessoas, Empresa/Instituição
- **Detecção automática**: Reconhece acrônimos, códigos de herbário, instituições
- **Índice de confiança**: Score de 0.0 a 1.0 para cada classificação
- **Padrões avançados**: Detecta "EMBRAPA", "Pesquisas da Biodiversidade", "USP", etc.
- **Classificação assistida**: Suporte para revisão manual de casos de baixa confiança

### 📊 Sistema de Canonicalização Avançado
- **Algoritmo de similaridade**: Combina análise fonética, inicial e sobrenome
- **Scoring inteligente**: Calcula confiança na canonicalização
- **Revisão automática**: Identifica casos que necessitam validação manual

## Visão Geral

O algoritmo resolve o problema de múltiplas representações do mesmo coletor (ex: "FORZZA", "Forzza, R." e "R.C. Forzza") através de:

1. **Atomização**: Separação de múltiplos coletores em uma string
2. **Normalização**: Padronização de cada nome individual
3. **Canonicalização**: Agrupamento de variações da mesma pessoa

## Estrutura do Projeto

```
coletores/
├── src/                          # Código fonte
│   ├── canonicalizador_coletores.py  # Classes principais do algoritmo
│   ├── analise_coletores.py          # Script de análise exploratória
│   ├── processar_coletores.py        # Script de processamento principal
│   ├── validar_canonicalizacao.py    # Script de validação
│   └── gerar_relatorios.py           # Script de geração de relatórios
├── config/                       # Configurações
│   └── mongodb_config.py            # Configuração do MongoDB e algoritmo
├── logs/                         # Arquivos de log
├── reports/                      # Relatórios gerados
├── requirements.txt              # Dependências Python
└── README.md                     # Esta documentação
```

## Instalação

1. **Instalar dependências**:
```bash
pip install -r requirements.txt
```

2. **Configurar MongoDB**:
   - Verificar string de conexão em `config/mongodb_config.py`
   - Banco: `dwc2json`
   - Coleções: `ocorrências` (origem) e `coletores` (destino)

## Uso

### Scripts Disponíveis

O sistema é composto por quatro scripts principais, cada um com funcionalidades específicas:

| Script | Descrição | Documentação |
|--------|-----------|--------------|
| `analise_coletores.py` | Análise exploratória dos dados | [📖 Documentação](docs/analise_coletores.md) |
| `processar_coletores.py` | Processamento principal e canonicalização | [📖 Documentação](docs/processar_coletores.md) |
| `validar_canonicalizacao.py` | Validação de qualidade dos resultados | [📖 Documentação](docs/validar_canonicalizacao.md) |
| `gerar_relatorios.py` | Geração de relatórios detalhados | [📖 Documentação](docs/gerar_relatorios.md) |

### 1. Análise Exploratória

Primeiro, execute uma análise para entender os padrões dos dados:

```bash
cd src
python analise_coletores.py
```

**Novos recursos**:
- ✅ Amostragem estratificada: 100k registros de Plantae + 100k de Animalia
- ✅ Sistema de classificação de entidades com 3 categorias
- ✅ Índice de confiança para classificação (0.0-1.0)
- ✅ Detecção de empresas/instituições (ex: "EMBRAPA", "USP", "RB")
- ✅ Análise por kingdom especializado

**Saída**: Relatório em `reports/` com:
- Distribuição por tipo de entidade (pessoa/grupo/empresa)
- Estatísticas de confiança na classificação
- Distribuição de formatos de nomes por kingdom
- Separadores mais comuns
- Exemplos classificados por tipo com score de confiança
- Caracteres especiais identificados
- Amostras por padrão detectado

### 2. Processamento Principal

Execute a canonicalização de todos os dados:

```bash
# Processamento completo (11M registros)
python processar_coletores.py

# Reiniciar do zero (limpa dados existentes)
python processar_coletores.py --restart

# Ver casos que precisam revisão manual
python processar_coletores.py --revisao
```

**Melhorias implementadas**:
- ✅ Suporte a análise por kingdom (Plantae/Animalia)
- ✅ Identificação de tipos: pessoa vs grupo/projeto
- ✅ Estrutura expandida com estatísticas por reino

**Características**:
- Processamento em lotes (10k registros por vez)
- Sistema de checkpoint para recuperação
- Logging verboso
- Interrupção controlada (Ctrl+C)

### 3. Validação

Valide a qualidade da canonicalização:

```bash
# Validação completa
python validar_canonicalizacao.py

# Exportar amostra para revisão manual
python validar_canonicalizacao.py --csv validacao_manual.csv
```

**Funcionalidades de validação**:
- Análise de qualidade por kingdom
- Detecção de especialização de coletores
- Identificação de casos problemáticos
- Recomendações automatizadas

### 4. Relatórios

Gere relatórios detalhados:

```bash
# Todos os relatórios
python gerar_relatorios.py

# Relatório específico
python gerar_relatorios.py --tipo estatisticas
python gerar_relatorios.py --tipo top --top-n 50
python gerar_relatorios.py --tipo csv
```

**Novos tipos de relatório**:
- Análise comparativa por kingdom
- Coletores especialistas vs generalistas
- Estatísticas de grupos/projetos
- Métricas de qualidade avançadas

## Algoritmo

### Classes Principais

#### `AtomizadorNomes`
- Separa múltiplos coletores usando padrões regex
- Suporta separadores: `&`, `e`, `and`, `;`, `et al.`, `e col.`, etc.
- Valida nomes resultantes

#### `NormalizadorNome`
- Extrai componentes: sobrenome, iniciais, nome completo
- Gera chaves de busca fonética (Soundex, Metaphone)
- Normaliza para comparação

#### `CanonizadorColetores`
- Agrupa variações do mesmo coletor
- Calcula similaridade usando:
  - Sobrenome (peso 50%)
  - Compatibilidade de iniciais (peso 30%)
  - Similaridade fonética (peso 20%)
- Score de confiança para agrupamento

#### `GerenciadorMongoDB`
- Interface com banco de dados
- Operações em lote otimizadas
- Sistema de checkpoint
- Índices para busca eficiente

### Estrutura da Coleção `coletores`

```json
{
  "_id": ObjectId("..."),
  "coletor_canonico": "Forzza, R.C.",
  "sobrenome_normalizado": "forzza",
  "iniciais": ["R", "C"],
  "variacoes": [
    {
      "forma_original": "FORZZA",
      "frequencia": 1250,
      "primeira_ocorrencia": ISODate("..."),
      "ultima_ocorrencia": ISODate("...")
    }
  ],
  "total_registros": 4200,
  "confianca_canonicalizacao": 0.95,
  "kingdoms": {
    "Plantae": 2800,
    "Animalia": 1400
  },
  "tipo_coletor": "pessoa",  // "pessoa", "grupo_pessoas" ou "empresa_instituicao"
  "confianca_tipo_coletor": 0.85,  // Confiança na classificação do tipo (0.0-1.0)
  "metadados": {
    "data_criacao": ISODate("..."),
    "ultima_atualizacao": ISODate("..."),
    "algoritmo_versao": "1.0",
    "revisar_manualmente": false
  },
  "indices_busca": {
    "soundex": "F620",
    "metaphone": "FRTS"
  }
}
```

## Configuração

### Parâmetros Principais (`config/mongodb_config.py`)

- `similarity_threshold`: 0.85 (limiar de similaridade para agrupamento)
- `confidence_threshold`: 0.7 (limiar de confiança automática)
- `batch_size`: 10000 (registros por lote)
- `sample_size`: 100000 (tamanho da amostra para análise)

### Padrões de Separação

Personalizáveis em `SEPARATOR_PATTERNS`:
- `&` ou `e`
- `and`
- `;`
- `, + maiúscula`
- `et al.`
- `e col.`

## Logs

Todos os scripts geram logs detalhados em `logs/`:
- `analise_exploratoria.log`
- `processamento.log`
- `validacao.log`
- `relatorios.log`

## Performance

### Estimativas (11M registros)

- **Processamento inicial**: 6-8 horas
- **Performance**: ~500 registros/segundo
- **Memória**: ~2GB RAM
- **Armazenamento**: ~5GB adicional no MongoDB

### Otimizações

- Processamento em lotes
- Índices MongoDB otimizados
- Cache interno do canonizador
- Checkpoints para recuperação

## Monitoramento

### Métricas de Qualidade

- Taxa de canonicalização (variações/coletor)
- Distribuição de confiança
- Casos que precisam revisão manual
- Inconsistências detectadas

### Relatórios Disponíveis

1. **Estatísticas Gerais**: Visão geral do processamento
2. **Top Coletores**: Coletores mais frequentes
3. **Qualidade**: Casos problemáticos e recomendações
4. **Variações**: Análise de padrões de nomes
5. **CSV Export**: Dados para análise externa

## Manutenção

### Revisão Manual

Casos marcados para revisão manual (`revisar_manualmente: true`):
- Confiança < 0.5
- Muitas variações com baixa confiança
- Sobrenomes inconsistentes

### Ajuste de Parâmetros

Para melhorar qualidade:
- Reduzir `similarity_threshold` (mais agrupamento)
- Aumentar `confidence_threshold` (mais revisão manual)
- Adicionar novos padrões de separação

## Troubleshooting

### Problemas Comuns

1. **Conexão MongoDB**:
   ```
   Erro: ServerSelectionTimeoutError
   ```
   - Verificar string de conexão
   - Confirmar acesso à rede

2. **Memória insuficiente**:
   - Reduzir `batch_size`
   - Aumentar RAM disponível

3. **Processamento lento**:
   - Verificar índices MongoDB
   - Ajustar `batch_size`

### Logs de Debug

Para mais detalhes, alterar nível de log:
```python
logging.basicConfig(level=logging.DEBUG)
```

## Desenvolvimento

### Extensões Futuras

1. **Algoritmos de similaridade avançados**:
   - Embedding de nomes
   - Redes neurais

2. **Interface web**:
   - Revisão manual facilitada
   - Visualização de resultados

3. **Integração**:
   - APIs REST
   - Exportação para outros formatos

### Testes

Para implementar testes:
```bash
# Estrutura sugerida
tests/
├── test_atomizador.py
├── test_normalizador.py
├── test_canonizador.py
└── test_mongodb.py
```

## Contribuição

1. Fork do projeto
2. Criar branch para feature
3. Implementar com testes
4. Documentar mudanças
5. Pull request

## Licença

Este projeto está sob licença [inserir licença apropriada].

## Contato

Para dúvidas ou sugestões, contactar [inserir contato].