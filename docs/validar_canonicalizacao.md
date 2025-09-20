# Documentação: validar_canonicalizacao.py

## Descrição
O script `validar_canonicalizacao.py` realiza uma análise de qualidade dos resultados da canonicalização, identificando possíveis problemas, inconsistências e casos que necessitam revisão manual. É essencial para garantir a precisão do processo de canonicalização.

## Funcionalidades Principais

### 1. Análise de Qualidade Global
- **Distribuição de confiança**: Análise dos scores de canonicalização
- **Taxa de canonicalização**: Razão variações/coletor canônico
- **Detecção de outliers**: Coletores com comportamento anômalo
- **Métricas de consistência**: Avaliação da homogeneidade dos grupos

### 2. Identificação de Casos Problemáticos
- **Baixa confiança**: Coletores com score < 0.5
- **Sobrenomes inconsistentes**: Variações com sobrenomes diferentes
- **Grupos muito grandes**: Coletores com muitas variações suspeitas
- **Mistura de tipos**: Pessoas e projetos agrupados incorretamente

### 3. Validação por Kingdom
- **Análise separada**: Plantae vs Animalia
- **Especialização detectada**: Coletores especializados em um reino
- **Crossover analysis**: Coletores que trabalham com ambos os reinos

### 4. Exportação para Revisão Manual
- **Formato CSV**: Para análise em planilhas
- **Amostragem estratificada**: Casos representativos
- **Priorização**: Casos mais críticos primeiro

## Algoritmos de Validação

### 1. Análise de Confiança
```python
def analisar_confianca(coletor):
    confianca = coletor['confianca_canonicalizacao']

    if confianca >= 0.95:
        return "Muito Alta"
    elif confianca >= 0.85:
        return "Alta"
    elif confianca >= 0.70:
        return "Média"
    elif confianca >= 0.50:
        return "Baixa"
    else:
        return "Muito Baixa"
```

### 2. Detecção de Inconsistências
```python
def detectar_inconsistencias(coletor):
    problemas = []

    # Sobrenomes muito diferentes
    sobrenomes = set()
    for variacao in coletor['variacoes']:
        sobrenome = extrair_sobrenome(variacao['forma_original'])
        sobrenomes.add(sobrenome)

    if len(sobrenomes) > 3:
        problemas.append("sobrenomes_inconsistentes")

    # Muitas variações com baixa frequência
    variacoes_raras = [v for v in coletor['variacoes'] if v['frequencia'] == 1]
    if len(variacoes_raras) > 10:
        problemas.append("muitas_variacoes_raras")

    return problemas
```

### 3. Análise de Especialização por Kingdom
```python
def analisar_especializacao(coletor):
    kingdoms = coletor['kingdoms']
    total = sum(kingdoms.values())

    for kingdom, count in kingdoms.items():
        percentual = count / total
        if percentual >= 0.9:
            return f"especialista_{kingdom.lower()}"

    return "generalista"
```

## Métricas de Qualidade

### 1. Métricas Globais
- **Taxa de canonicalização média**: Variações por coletor
- **Distribuição de confiança**: % em cada faixa
- **Taxa de revisão manual**: % que precisa revisão
- **Cobertura por kingdom**: Distribuição entre reinos

### 2. Métricas por Coletor
- **Score de confiança**: 0.0 a 1.0
- **Número de variações**: Indicador de complexidade
- **Consistência de sobrenome**: Similaridade entre variações
- **Especialização**: Concentração em um kingdom

### 3. Métricas de Inconsistência
- **Sobrenomes conflitantes**: Variações com sobrenomes muito diferentes
- **Frequências desbalanceadas**: Uma variação domina o grupo
- **Tipos misturados**: Pessoas e projetos no mesmo grupo

## Estrutura dos Relatórios

### 1. Relatório de Qualidade Geral
```
================================================================================
RELATÓRIO DE VALIDAÇÃO DA CANONICALIZAÇÃO
================================================================================
Data/Hora: 2025-09-20 14:30:45

ESTATÍSTICAS GERAIS
----------------------------------------
Total de coletores canônicos: 45,623
Coletores de alta qualidade (≥0.85): 38,901 (85.3%)
Coletores de qualidade média (0.70-0.84): 5,234 (11.5%)
Coletores de baixa qualidade (<0.70): 1,488 (3.2%)
Taxa média de canonicalização: 3.8 variações/coletor

DISTRIBUIÇÃO POR KINGDOM
----------------------------------------
Especialistas em Plantae: 28,450 (62.4%)
Especialistas em Animalia: 15,120 (33.1%)
Generalistas (ambos): 2,053 (4.5%)

CASOS PROBLEMÁTICOS IDENTIFICADOS
----------------------------------------
Sobrenomes inconsistentes: 234 casos
Muitas variações raras: 156 casos
Grupos muito grandes (>20 variações): 89 casos
Confiança muito baixa (<0.3): 45 casos
```

### 2. Relatório Detalhado de Casos Problemáticos
```json
{
  "coletor_id": "64f8a9b12345678901234567",
  "coletor_canonico": "Silva",
  "problemas": [
    "sobrenomes_inconsistentes",
    "muitas_variacoes_raras"
  ],
  "confianca": 0.25,
  "total_variacoes": 23,
  "kingdoms": {"Plantae": 45, "Animalia": 12},
  "variacoes_problematicas": [
    {"forma_original": "Silveira, J.", "frequencia": 1},
    {"forma_original": "Santos, M.", "frequencia": 1},
    {"forma_original": "Silva Project", "frequencia": 3}
  ],
  "recomendacao": "dividir_grupo"
}
```

### 3. Exportação CSV para Revisão Manual
```csv
coletor_canonico,confianca,total_registros,num_variacoes,problemas,kingdoms_plantae,kingdoms_animalia,principal_variacao,recomendacao
"Silva, J.C.",0.95,1250,3,nenhum,800,450,"Silva, J.",manter
"Santos",0.35,89,15,"sobrenomes_inconsistentes",45,44,"Santos, M.","dividir_grupo"
"Pesquisas Bio",0.85,234,1,nenhum,234,0,"Pesquisas da Biodiversidade",manter_grupo
```

## Configuração

### Parâmetros de Validação
```python
# config/mongodb_config.py
VALIDATION_CONFIG = {
    'confianca_minima': 0.5,
    'max_variacoes_suspeitas': 20,
    'threshold_especializacao': 0.9,
    'sample_size_revisao': 1000
}
```

### Critérios de Qualidade
```python
QUALITY_THRESHOLDS = {
    'alta_qualidade': 0.85,
    'qualidade_media': 0.70,
    'baixa_qualidade': 0.50,
    'revisao_obrigatoria': 0.30
}
```

## Execução

### Comandos Disponíveis

#### Validação Completa
```bash
cd src/
python validar_canonicalizacao.py
```

#### Exportar Amostra para CSV
```bash
python validar_canonicalizacao.py --csv validacao_manual.csv
```

#### Validação de Casos Específicos
```bash
python validar_canonicalizacao.py --filtro baixa_confianca
python validar_canonicalizacao.py --filtro inconsistencias
```

### Opções de Linha de Comando
- `--csv ARQUIVO`: Exporta amostra para revisão manual
- `--filtro TIPO`: Filtra tipos específicos de problemas
- `--kingdom REINO`: Analisa apenas um kingdom
- `--sample-size N`: Tamanho da amostra para export

## Tipos de Problemas Detectados

### 1. Sobrenomes Inconsistentes
**Descrição**: Variações com sobrenomes muito diferentes agrupadas
```
Coletor: "Silva"
Variações problemáticas:
- Silva, J. (freq: 100)
- Silveira, M. (freq: 80)  ← Suspeito
- Santos, A. (freq: 50)    ← Suspeito
```

### 2. Muitas Variações Raras
**Descrição**: Muitas formas com frequência 1, pode indicar ruído
```
Coletor: "Santos"
Total variações: 25
Variações raras (freq=1): 18
```

### 3. Grupos Muito Grandes
**Descrição**: Coletores com número excessivo de variações
```
Coletor: "Silva"
Total variações: 45
Pode indicar: sobrenome comum demais para agrupar
```

### 4. Confiança Muito Baixa
**Descrição**: Score de canonicalização inferior a 0.3
```
Coletor: "Costa"
Confiança: 0.15
Indicador: agrupamento muito incerto
```

### 5. Tipos Misturados
**Descrição**: Pessoas e projetos no mesmo grupo
```
Coletor: "Silva Research"
Variações:
- Silva, J. (pessoa)
- Silva Research Team (projeto)
- Silva Lab (laboratório)
```

## Recomendações de Ação

### 1. Manter Grupo
- **Critério**: Confiança ≥ 0.85 e sem problemas detectados
- **Ação**: Nenhuma intervenção necessária

### 2. Revisar Manualmente
- **Critério**: Confiança 0.5-0.84 ou problemas menores
- **Ação**: Validação humana recomendada

### 3. Dividir Grupo
- **Critério**: Sobrenomes inconsistentes ou tipos misturados
- **Ação**: Separar em múltiplos coletores canônicos

### 4. Remover Variações
- **Critério**: Muitas variações raras ou ruído evidente
- **Ação**: Limpar variações de baixa qualidade

### 5. Refazer Canonicalização
- **Critério**: Confiança < 0.3 ou problemas graves
- **Ação**: Reprocessar com parâmetros ajustados

## Análise por Kingdom

### Coletores Especialistas
```python
# Exemplo: Especialista em Plantae
{
  "coletor_canonico": "Silva, J.C.",
  "kingdoms": {"Plantae": 950, "Animalia": 50},
  "especializacao": "botânico",
  "percentual_especializacao": 95.0
}
```

### Coletores Generalistas
```python
# Exemplo: Trabalha com ambos os reinos
{
  "coletor_canonico": "Santos, M.A.",
  "kingdoms": {"Plantae": 480, "Animalia": 520},
  "especializacao": "generalista",
  "percentual_especializacao": 52.0
}
```

## Métricas de Performance

### Tempo de Execução
- **45.000 coletores**: ~5-10 minutos
- **Performance**: ~100-200 coletores/segundo
- **Memória**: ~1GB RAM

### Fatores de Performance
- **Número de coletores**: Linear
- **Complexidade das variações**: Quadrático
- **Filtros aplicados**: Afeta tempo de consulta

## Integração com Workflow

### Sequência Recomendada
1. `analise_coletores.py` - Análise exploratória
2. `processar_coletores.py` - Canonicalização
3. **`validar_canonicalizacao.py`** - Validação de qualidade
4. Revisão manual dos casos problemáticos
5. `gerar_relatorios.py` - Relatórios finais

### Feedback Loop
```
Validação → Identificação de Problemas → Ajuste de Parâmetros → Reprocessamento
```

## Troubleshooting

### Problemas Comuns

1. **Muitos Casos para Revisão (>10%)**
   - Reduzir `similarity_threshold` no processamento
   - Ajustar padrões de separação
   - Verificar qualidade dos dados de entrada

2. **Falsos Positivos na Detecção**
   - Ajustar thresholds de validação
   - Refinar algoritmos de detecção
   - Adicionar whitelist de exceções

3. **Performance Lenta**
   - Criar índices adicionais no MongoDB
   - Processar por batches
   - Usar filtros para reduzir escopo

## Exemplo de Uso Programático
```python
from validar_canonicalizacao import ValidadorCanonicalizacao

# Inicializar validador
validador = ValidadorCanonicalizacao()

# Executar validação completa
resultados = validador.validar_todos()

# Exportar casos problemáticos
validador.exportar_casos_problematicos(
    arquivo="revisao_manual.csv",
    filtro="baixa_confianca"
)

# Obter estatísticas
estatisticas = validador.obter_estatisticas()
print(f"Taxa de qualidade: {estatisticas['taxa_alta_qualidade']:.1f}%")
```