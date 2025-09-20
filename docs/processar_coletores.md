# Documentação: processar_coletores.py

## Descrição
O script `processar_coletores.py` é o módulo principal do sistema de canonicalização. Ele processa todos os registros da base de dados MongoDB, aplicando algoritmos de normalização e canonicalização para identificar e agrupar variações do mesmo coletor.

## Funcionalidades Principais

### 1. Processamento em Lotes
- **Tamanho do lote**: 10.000 registros (configurável)
- **Processamento sequencial**: Para controle de memória
- **Checkpoint automático**: Recuperação em caso de interrupção

### 2. Canonicalização de Nomes
- **Atomização**: Separação de múltiplos coletores
- **Normalização**: Padronização de formatos
- **Agrupamento**: Identificação de variações do mesmo coletor
- **Scoring**: Cálculo de confiança na canonicalização

### 3. Detecção de Tipos
- **Pessoas**: Coletores individuais com nome próprio único
- **Conjunto de Pessoas**: Múltiplos nomes próprios para atomização
- **Grupos Genéricos**: Denominações sem nomes próprios específicos
- **Empresas/Instituições**: Organizações, universidades, códigos
- **Análise por Kingdom**: Plantae, Animalia, etc.

### 4. Sistema de Recuperação
- **Checkpoints**: Salvamento de progresso a cada 50.000 registros
- **Reinício controlado**: Continua de onde parou
- **Interrupção segura**: Ctrl+C preserva dados

## Estrutura de Processamento

### Pipeline de Dados
```
MongoDB (ocorrencias) → Lotes → Atomização → Normalização → Canonicalização → MongoDB (coletores)
```

### Fluxo Detalhado
1. **Leitura**: Obtém lote de registros da coleção `ocorrencias`
2. **Validação**: Filtra registros válidos com `recordedBy`
3. **Atomização**: Separa múltiplos coletores por registro
4. **Normalização**: Extrai componentes (sobrenome, iniciais, etc.)
5. **Canonicalização**: Agrupa variações do mesmo coletor
6. **Persistência**: Salva/atualiza na coleção `coletores`

## Algoritmos Principais

### AtomizadorNomes
Separa múltiplos coletores usando padrões regex:
```python
# Exemplo de entrada
"Silva, J. & Santos, M.; Costa et al."

# Resultado da atomização
["Silva, J.", "Santos, M.", "Costa et al."]
```

### NormalizadorNome
Extrai componentes estruturados:
```python
# Entrada: "Silva, J.C."
{
    'nome_original': 'Silva, J.C.',
    'nome_normalizado': 'Silva, J.C.',
    'sobrenome_normalizado': 'silva',
    'iniciais': ['J', 'C'],
    'tipo_coletor': 'pessoa',
    'kingdoms': {'Plantae': 1},
    'chaves_busca': {
        'soundex': 'S400',
        'metaphone': 'SLV'
    }
}
```

### CanonizadorColetores
Agrupa variações usando algoritmo de similaridade:

#### Cálculo de Similaridade
- **Sobrenome** (peso 50%): Comparação exata e fonética
- **Iniciais** (peso 30%): Compatibilidade e sobreposição
- **Similaridade fonética** (peso 20%): Soundex e Metaphone

#### Threshold de Agrupamento
- **≥ 0.85**: Agrupa automaticamente
- **0.70-0.84**: Agrupa com revisão manual
- **< 0.70**: Cria novo coletor canônico

## Estrutura da Coleção `coletores`

### Documento Canônico
```json
{
  "_id": ObjectId("..."),
  "coletor_canonico": "Silva, J.C.",
  "sobrenome_normalizado": "silva",
  "iniciais": ["J", "C"],
  "variacoes": [
    {
      "forma_original": "SILVA",
      "frequencia": 1250,
      "primeira_ocorrencia": ISODate("..."),
      "ultima_ocorrencia": ISODate("...")
    },
    {
      "forma_original": "Silva, J.",
      "frequencia": 800,
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
  "tipo_coletor": "pessoa",
  "metadados": {
    "data_criacao": ISODate("..."),
    "ultima_atualizacao": ISODate("..."),
    "algoritmo_versao": "1.0",
    "revisar_manualmente": false
  },
  "indices_busca": {
    "soundex": "S400",
    "metaphone": "SLV"
  }
}
```

## Configuração

### Parâmetros Principais
```python
# config/mongodb_config.py
ALGORITHM_CONFIG = {
    'batch_size': 10000,
    'similarity_threshold': 0.85,
    'confidence_threshold': 0.7,
    'checkpoint_interval': 50000
}
```

### Otimização de Performance
```python
# Índices MongoDB recomendados
db.coletores.createIndex({"sobrenome_normalizado": 1})
db.coletores.createIndex({"variacoes.forma_original": 1})
db.coletores.createIndex({"indices_busca.soundex": 1})
```

## Execução

### Comandos Disponíveis

#### Processamento Completo
```bash
cd src/
python processar_coletores.py
```

#### Reiniciar do Zero
```bash
python processar_coletores.py --restart
```

#### Revisar Casos Problemáticos
```bash
python processar_coletores.py --revisao
```

### Opções de Linha de Comando
- `--restart`: Limpa dados existentes e reinicia
- `--revisao`: Mostra casos que precisam revisão manual
- `--batch-size N`: Define tamanho do lote
- `--checkpoint-interval N`: Intervalo de checkpoint

## Sistema de Checkpoints

### Funcionamento
1. **Salvamento automático**: A cada 50.000 registros processados
2. **Arquivo de estado**: `checkpoints/processamento_estado.json`
3. **Recuperação**: Reinicia automaticamente do último checkpoint

### Estrutura do Checkpoint
```json
{
  "ultimo_id": ObjectId("..."),
  "registros_processados": 250000,
  "timestamp": "2025-09-20T10:30:00Z",
  "estatisticas": {
    "coletores_criados": 15420,
    "variantes_agrupadas": 89650,
    "casos_revisao": 1230
  }
}
```

## Métricas de Performance

### Estimativas para 11M Registros
- **Tempo total**: 6-8 horas
- **Performance**: ~500 registros/segundo
- **Memória**: ~2GB RAM
- **Armazenamento adicional**: ~5GB MongoDB

### Fatores de Performance
- **Tamanho do lote**: Maior = mais rápido, mais memória
- **Índices MongoDB**: Críticos para busca eficiente
- **Complexidade dos nomes**: Mais variações = mais lento
- **Hardware**: CPU, RAM e velocidade do disco

## Monitoramento e Logs

### Arquivo de Log
- **Localização**: `../logs/processamento.log`
- **Nível**: DEBUG para arquivo, INFO para console
- **Rotação**: 10MB por arquivo, 5 backups

### Métricas em Tempo Real
```
2025-09-20 10:30:15 - INFO - Processando lote 251/1100 (22.8%)
2025-09-20 10:30:15 - INFO - Registros processados: 250,000/11,000,000
2025-09-20 10:30:15 - INFO - Performance: 485 reg/s
2025-09-20 10:30:15 - INFO - Novos coletores: 15,420
2025-09-20 10:30:15 - INFO - Variantes agrupadas: 89,650
2025-09-20 10:30:15 - INFO - Tempo estimado restante: 5h 23m
```

## Casos de Revisão Manual

### Critérios para Revisão
- **Confiança < 0.5**: Baixa certeza na canonicalização
- **Muitas variações**: Mais de 20 formas diferentes
- **Sobrenomes inconsistentes**: Possível erro de agrupamento
- **Grupos misturados**: Pessoas e projetos no mesmo grupo

### Exemplo de Caso Problemático
```json
{
  "coletor_canonico": "Silva",
  "confianca_canonicalizacao": 0.35,
  "revisar_manualmente": true,
  "variacoes": [
    {"forma_original": "Silva, J.", "frequencia": 100},
    {"forma_original": "Silva, M.", "frequencia": 95},
    {"forma_original": "Silveira, J.", "frequencia": 80},
    {"forma_original": "Silva Project", "frequencia": 25}
  ]
}
```

## Troubleshooting

### Problemas Comuns

1. **Memória Insuficiente**
   ```
   MemoryError: Unable to allocate array
   ```
   - Reduzir `batch_size` para 5000
   - Verificar RAM disponível
   - Fechar outras aplicações

2. **Conexão MongoDB Perdida**
   ```
   AutoReconnect: connection closed
   ```
   - Aumentar `serverSelectionTimeoutMS`
   - Verificar estabilidade da rede
   - Usar connection pooling

3. **Checkpoint Corrompido**
   ```
   JSONDecodeError: Expecting value
   ```
   - Deletar arquivo `checkpoints/processamento_estado.json`
   - Reiniciar com `--restart`

4. **Performance Lenta**
   - Verificar índices MongoDB
   - Ajustar `batch_size`
   - Monitorar uso de CPU/RAM

### Comandos de Diagnóstico
```bash
# Verificar índices
db.coletores.getIndexes()

# Estatísticas da coleção
db.coletores.stats()

# Monitorar operações
db.currentOp()
```

## Exemplo de Uso Programático
```python
from processar_coletores import ProcessadorColetores

# Inicializar processador
processador = ProcessadorColetores(
    mongodb_config=MONGODB_CONFIG,
    algorithm_config=ALGORITHM_CONFIG
)

# Processar todos os dados
resultado = processador.processar_todos()

print(f"Processados: {resultado['registros_processados']}")
print(f"Coletores criados: {resultado['coletores_criados']}")
print(f"Casos para revisão: {resultado['casos_revisao']}")
```

## Integração com Outros Scripts
- **Pré-requisito**: Execute `analise_coletores.py` primeiro
- **Sequência**: `processar_coletores.py` → `validar_canonicalizacao.py`
- **Relatórios**: Use `gerar_relatorios.py` após o processamento